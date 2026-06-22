"""Architecture de base du système d'enrichissement.

BaseEnricher définit le contrat de chaque enrichisseur.
Le registre associe les types d'IOC aux enrichisseurs pertinents.
orchestrate() est le point d'entrée unique : appelle tous les enrichisseurs
applicables pour un indicateur donné et persiste les résultats.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime

from app.models import Indicator
from app.models.enrichment import Enrichment
from app.models.enums import IOCType

logger = logging.getLogger(__name__)


class BaseEnricher(ABC):
    """Contrat minimal de chaque enrichisseur.

    provider  : identifiant court unique (ex: 'geoip', 'whois', 'dns')
    ioc_types : liste des IOCType que cet enrichisseur sait traiter
    """
    provider: str
    ioc_types: list[IOCType]

    @abstractmethod
    def enrich(self, indicator: Indicator) -> dict:
        """Retourne un dict de données d'enrichissement, ou {} en cas d'échec.
        Ne doit jamais lever d'exception — toujours capturer et logger."""


# Registre : liste des enrichisseurs disponibles dans l'ordre d'appel.
# On les instancie ici une seule fois (lazy import pour éviter les imports
# circulaires au démarrage si les modules ne sont pas encore créés).
def _build_registry() -> list[BaseEnricher]:
    from enrichment.geoip import GeoIPEnricher
    from enrichment.dns_lookup import DNSEnricher
    from enrichment.whois import WHOISEnricher
    return [
        GeoIPEnricher(),
        DNSEnricher(),
        WHOISEnricher(),
    ]


_registry: list[BaseEnricher] | None = None


def get_registry() -> list[BaseEnricher]:
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def orchestrate(indicator: Indicator, session) -> dict[str, dict]:
    """Enrichit un indicateur avec tous les enrichisseurs applicables.

    Pour chaque enrichisseur dont le type matche :
      1. Appelle enrich()
      2. Upserte le résultat dans la table enrichments
         (INSERT ... ON CONFLICT DO UPDATE pour l'idempotence)

    Retourne un dict {provider: data} avec tous les résultats obtenus.
    """
    results: dict[str, dict] = {}

    for enricher in get_registry():
        if indicator.type not in enricher.ioc_types:
            continue

        try:
            data = enricher.enrich(indicator)
        except Exception as e:
            logger.error(f"[{enricher.provider}] Erreur inattendue sur {indicator.value!r}: {e}")
            data = {}

        if not data:
            continue

        # Upsert : update si le provider existe déjà pour cet indicator
        existing = (
            session.query(Enrichment)
            .filter_by(indicator_id=indicator.id, provider=enricher.provider)
            .first()
        )
        if existing:
            existing.data = data
            existing.enriched_at = datetime.utcnow()
        else:
            session.add(Enrichment(
                indicator_id=indicator.id,
                provider=enricher.provider,
                data=data,
                enriched_at=datetime.utcnow(),
            ))

        results[enricher.provider] = data
        logger.debug(f"[{enricher.provider}] {indicator.value!r} enrichi")

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur commit enrichissement: {e}")

    return results