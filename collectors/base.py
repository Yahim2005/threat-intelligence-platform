"""BaseCollector : squelette réutilisable pour tous les collecteurs TIP.

Chaque source hérite de cette classe et n'implémente que :
  - name        : str identifiant la source (doit correspondre à Source.name en base)
  - fetch()     : télécharge / récupère les données brutes
  - parse(raw)  : traduit les données brutes en liste de records standards

Le reste (boucle, persistance, logging, gestion du temps, retries réseau,
journalisation des runs) est fourni par run() et http_get_with_retry().
"""
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime

import httpx

from app.database import SessionLocal
from app.models import CollectionRun, Source
from app.models.enums import RunStatus
from app.persistence import store_records

logger = logging.getLogger(__name__)

# Valeurs par défaut, surchageables par sous-classe si besoin.
DEFAULT_TIMEOUT = 30          # secondes, par requête HTTP
DEFAULT_MAX_RETRIES = 3       # nombre de tentatives avant abandon
DEFAULT_BACKOFF_BASE = 2      # secondes ; le délai double à chaque échec : 2s, 4s, 8s...


class BaseCollector(ABC):
    name: str
    timeout: int = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_base: int = DEFAULT_BACKOFF_BASE

    # ------------------------------------------------------------------ #
    #  Méthodes abstraites — à implémenter dans chaque sous-classe        #
    # ------------------------------------------------------------------ #
    @abstractmethod
    def fetch(self):
        """Récupère les données brutes depuis la source.
        Peut retourner n'importe quoi (str CSV, dict JSON, bytes…) :
        c'est parse() qui sait quoi en faire.
        Doit lever une exception en cas d'erreur réseau."""

    @abstractmethod
    def parse(self, raw) -> list[dict]:
        """Traduit les données brutes en liste de records standards.
        Chaque record est un dict avec ces clés :
            value      (str)       : valeur de l'IOC — obligatoire
            type       (IOCType)   : type de l'IOC  — obligatoire
            seen_at    (datetime)  : date d'observation — optionnel
            metadata   (dict)      : métadonnées brutes de la source — optionnel
            tag_names  (list[str]) : tags normalisés (ex. "kev", "tor-exit") — optionnel
            context    (dict)      : détails du sighting — optionnel
        """

    # ------------------------------------------------------------------ #
    #  Helper HTTP réutilisable — retries + backoff exponentiel           #
    # ------------------------------------------------------------------ #
    def http_get_with_retry(self, url: str, **kwargs) -> httpx.Response:
        """GET HTTP avec retries automatiques en cas d'erreur réseau ou HTTP 5xx/429.
        kwargs est transmis directement à httpx.get (params, headers, etc.).
        Lève la dernière exception rencontrée si toutes les tentatives échouent.
        """
        kwargs.setdefault("timeout", self.timeout)
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = httpx.get(url, **kwargs)
                # 429 (rate limit) et 5xx (erreur serveur) méritent un retry.
                # 4xx hors 429 (ex: 404, 401) sont des erreurs définitives : pas la peine de réessayer.
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                last_exception = e
                status = e.response.status_code
                if status == 429 or status >= 500:
                    logger.warning(
                        f"[{self.name}] Tentative {attempt}/{self.max_retries} "
                        f"échouée (HTTP {status}) : {e}"
                    )
                else:
                    # Erreur définitive (404, 401...), inutile de réessayer.
                    raise
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                logger.warning(
                    f"[{self.name}] Tentative {attempt}/{self.max_retries} "
                    f"échouée (réseau) : {e}"
                )

            if attempt < self.max_retries:
                delay = self.backoff_base ** attempt
                logger.info(f"[{self.name}] Nouvelle tentative dans {delay}s...")
                time.sleep(delay)

        raise last_exception

    # ------------------------------------------------------------------ #
    #  run() — le squelette, générique, ne PAS surcharger                 #
    # ------------------------------------------------------------------ #
    def run(self):
        """Orchestre fetch → parse → persist. Même logique pour toutes les sources.
        Journalise systématiquement un CollectionRun, quel que soit le résultat.
        Isolation des pannes : aucune exception ne sort de cette méthode.
        """
        source_name = self.name
        logger.info(f"[{source_name}] Collecteur démarré")
        start_time = time.time()
        started_at = datetime.utcnow()

        run_session = SessionLocal()
        run_log_id = None
        try:
            source = run_session.query(Source).filter_by(name=source_name).first()
            if source:
                run_log = CollectionRun(
                    source_id=source.id,
                    started_at=started_at,
                    status=RunStatus.running,
                )
                run_session.add(run_log)
                run_session.commit()
                run_log_id = run_log.id  # lu AVANT la fermeture de la session
        except Exception as e:
            logger.error(f"[{source_name}] Impossible de créer le CollectionRun : {e}")
        finally:
            run_session.close()

        def finalize(status: RunStatus, stats: dict | None = None, error: str | None = None):
            """Met à jour le CollectionRun avec le résultat final. Ne propage jamais d'exception."""
            if run_log_id is None:
                return
            session = SessionLocal()
            try:
                row = session.query(CollectionRun).filter_by(id=run_log_id).first()
                if row:
                    row.finished_at = datetime.utcnow()
                    row.status = status
                    if stats:
                        row.items_created = stats.get("created", 0)
                        row.items_updated = stats.get("updated", 0)
                        row.items_errors = stats.get("errors", 0)
                    if error:
                        row.error_message = error[:2048]
                    session.commit()
            except Exception as e:
                logger.error(f"[{source_name}] Impossible de finaliser le CollectionRun : {e}")
            finally:
                session.close()

        # 1. Récupération
        try:
            raw = self.fetch()
        except Exception as e:
            logger.error(f"[{source_name}] Erreur fetch : {e}")
            finalize(RunStatus.failed, error=f"fetch: {e}")
            return

        # 2. Parsing
        try:
            records = self.parse(raw)
        except Exception as e:
            logger.error(f"[{source_name}] Erreur parse : {e}")
            finalize(RunStatus.failed, error=f"parse: {e}")
            return

        logger.info(f"[{source_name}] {len(records)} records parsés")

        # 3. Persistance
        session = SessionLocal()
        try:
            stats = store_records(records, source_name, session)
        except Exception as e:
            logger.error(f"[{source_name}] Erreur persistance : {e}")
            finalize(RunStatus.failed, error=f"persistence: {e}")
            return
        finally:
            session.close()

        # 4. Log structuré final + journalisation du run
        duration = time.time() - start_time
        final_status = RunStatus.partial if stats.get("errors", 0) > 0 else RunStatus.success
        finalize(final_status, stats=stats)

        logger.info(
            f"[{source_name}] Terminé en {duration:.1f}s — "
            f"créés: {stats['created']} | "
            f"mis à jour: {stats['updated']} | "
            f"sightings: {stats['sightings']} | "
            f"erreurs: {stats['errors']}"
        )