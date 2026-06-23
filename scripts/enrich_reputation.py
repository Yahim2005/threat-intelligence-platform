#!/usr/bin/env python3
"""
Script de priorisation et d'exécution de l'enrichissement réputation.

Usage:
    python scripts/enrich_reputation.py --source abuseipdb --limit 500
    python scripts/enrich_reputation.py --source virustotal --limit 200
    python scripts/enrich_reputation.py --source all --limit 100 --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Permet d'importer les modules du projet depuis n'importe où
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import and_, or_, not_, exists, select
from sqlalchemy.orm import Session

from app.models import Indicator, ReputationCache
from app.models.enums import IndicatorStatus
from app.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("enrich_reputation")

CACHE_TTL_DAYS = 7
# Pause entre chaque requête API (secondes) pour respecter les quotas
RATE_LIMIT_DELAY = {
    "abuseipdb": 1.0,   # 1 req/sec → ~1000/jour confortablement
    "virustotal": 15.0,  # 4 req/min sur le plan gratuit
}


def get_candidates(session: Session, source: str, limit: int) -> list[Indicator]:
    """
    Retourne les indicateurs à enrichir, par ordre de priorité :
    1. Actifs uniquement
    2. Sans entrée de cache pour cette source (jamais enrichis)
    3. Avec cache expiré (> TTL jours)
    4. Triés par last_seen desc (les plus récents d'abord)
    """
    ttl_cutoff = datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS)

    # Sous-requête : indicateurs qui ont un cache frais pour cette source
    fresh_cache = (
        select(ReputationCache.indicator_id)
        .where(
            and_(
                ReputationCache.source == source,
                ReputationCache.fetched_at >= ttl_cutoff,
                ReputationCache.error.is_(None),
            )
        )
    )

    # Types supportés selon la source
    if source == "abuseipdb":
        supported_types = ["ip", "ipv6"]
    else:  # virustotal
        supported_types = ["ip", "ipv6", "domain", "md5", "sha1", "sha256", "url"]

    query = (
        session.query(Indicator)
        .filter(
            and_(
                Indicator.status == IndicatorStatus.active,
                Indicator.type.in_(supported_types),
                not_(Indicator.id.in_(fresh_cache)),
            )
        )
        .order_by(Indicator.last_seen.desc().nulls_last())
        .limit(limit)
    )

    return query.all()


def run_enrichment(source: str, limit: int, dry_run: bool) -> None:
    logger.info(
        "Démarrage enrichissement | source=%s | limit=%d | dry_run=%s",
        source, limit, dry_run,
    )

    sources_to_run = ["abuseipdb", "virustotal"] if source == "all" else [source]

    for src in sources_to_run:
        # Import dynamique selon la source
        if src == "abuseipdb":
            from enrichment.abuseipdb import enrich_indicator
        else:
            from enrichment.virustotal import enrich_indicator

        delay = RATE_LIMIT_DELAY[src]

        with SessionLocal() as session:
            candidates = get_candidates(session, src, limit)
            logger.info("%s: %d indicateurs candidats", src, len(candidates))

            if dry_run:
                for ind in candidates[:10]:
                    logger.info(
                        "  [DRY-RUN] %s | %s | last_seen=%s",
                        ind.type.value, ind.value, ind.last_seen,
                    )
                if len(candidates) > 10:
                    logger.info("  ... et %d autres", len(candidates) - 10)
                continue

            enriched = 0
            errors = 0

            for i, indicator in enumerate(candidates, 1):
                try:
                    result = enrich_indicator(session, indicator)
                    if result:
                        if result.error:
                            errors += 1
                            logger.warning(
                                "[%d/%d] %s ERREUR: %s",
                                i, len(candidates), indicator.value, result.error,
                            )
                        else:
                            enriched += 1
                            if src == "abuseipdb":
                                logger.info(
                                    "[%d/%d] %s → score=%s",
                                    i, len(candidates), indicator.value,
                                    result.abuse_confidence_score,
                                )
                            else:
                                logger.info(
                                    "[%d/%d] %s → %s/%s moteurs",
                                    i, len(candidates), indicator.value,
                                    result.vt_malicious, result.vt_total,
                                )
                except Exception as exc:
                    errors += 1
                    logger.error(
                        "[%d/%d] Exception inattendue pour %s: %s",
                        i, len(candidates), indicator.value, exc,
                    )

                # Pause entre chaque requête pour respecter le quota
                if i < len(candidates):
                    time.sleep(delay)

            logger.info(
                "%s terminé | enrichis=%d | erreurs=%d",
                src, enriched, errors,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrichissement réputation IOCs")
    parser.add_argument(
        "--source",
        choices=["abuseipdb", "virustotal", "all"],
        default="abuseipdb",
        help="Source de réputation à utiliser",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Nombre maximum d'indicateurs à enrichir",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les candidats sans appeler les APIs",
    )
    args = parser.parse_args()
    run_enrichment(args.source, args.limit, args.dry_run)


if __name__ == "__main__":
    main()
