"""BaseCollector : squelette réutilisable pour tous les collecteurs TIP.

Chaque source hérite de cette classe et n'implémente que :
  - name        : str identifiant la source (doit correspondre à Source.name en base)
  - fetch()     : télécharge / récupère les données brutes
  - parse(raw)  : traduit les données brutes en liste de records standards

Le reste (boucle, persistance, logging, gestion du temps) est fourni par run().
"""
import logging
import time
from abc import ABC, abstractmethod

from app.database import SessionLocal
from app.persistence import store_records

logger = logging.getLogger(__name__)


class BaseCollector(ABC):

    # Chaque sous-classe DOIT définir name comme attribut de classe.
    # Si elle ne le fait pas, run() lèvera une AttributeError explicite.
    name: str

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
            value   (str)      : valeur de l'IOC — obligatoire
            type    (IOCType)  : type de l'IOC  — obligatoire
            seen_at (datetime) : date d'observation — optionnel
            tags    (dict)     : métadonnées de l'indicateur — optionnel
            context (dict)     : détails du sighting — optionnel
        """

    # ------------------------------------------------------------------ #
    #  run() — le squelette, générique, ne PAS surcharger                 #
    # ------------------------------------------------------------------ #

    def run(self):
        """Orchestre fetch → parse → persist. Même logique pour toutes les sources."""
        source_name = self.name
        logger.info(f"[{source_name}] Collecteur démarré")
        start = time.time()

        # 1. Récupération
        try:
            raw = self.fetch()
        except Exception as e:
            logger.error(f"[{source_name}] Erreur fetch : {e}")
            return

        # 2. Parsing
        try:
            records = self.parse(raw)
        except Exception as e:
            logger.error(f"[{source_name}] Erreur parse : {e}")
            return

        logger.info(f"[{source_name}] {len(records)} records parsés")

        # 3. Persistance
        session = SessionLocal()
        try:
            stats = store_records(records, source_name, session)
        except Exception as e:
            logger.error(f"[{source_name}] Erreur persistance : {e}")
            return
        finally:
            session.close()

        # 4. Log structuré final
        duration = time.time() - start
        logger.info(
            f"[{source_name}] Terminé en {duration:.1f}s — "
            f"créés: {stats['created']} | "
            f"mis à jour: {stats['updated']} | "
            f"sightings: {stats['sightings']} | "
            f"erreurs: {stats['errors']}"
        )