#!/usr/bin/env python3
"""
Applique le mapping ATT&CK sur les indicateurs existants.

Usage:
    python scripts/map_attack.py --limit 1000 --dry-run
    python scripts/map_attack.py --limit 5000
    python scripts/map_attack.py --source openphish --limit 500
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models import Indicator
from app.models.enums import IndicatorStatus
from app.models.tag import Tag
from app.models.source import Source
from app.database import SessionLocal 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("map_attack")


def get_candidates(
    session: Session,
    limit: int,
    source_filter: str | None,
) -> list[Indicator]:
    """
    Retourne les indicateurs candidats au mapping ATT&CK, par priorité :
    1. Indicateurs actifs avec tags kind:* ou malware:*
    2. Indicateurs de sources connues (openphish, feodo, cisa, tor)
    3. Indicateurs de type CVE
    Triés par last_seen desc.
    """
    # Tags qui signalent un contexte tactique exploitable
    TACTICAL_TAG_PREFIXES = ["kind:", "malware:"]
    # Sources dont on connaît la spécialité tactique
    TACTICAL_SOURCES = ["openphish", "feodo", "cisa", "tor", "spamhaus", "threatfox"]

    query = session.query(Indicator).options(
        joinedload(Indicator.tags),
        joinedload(Indicator.source),
    ).filter(
        Indicator.status == IndicatorStatus.active
    )

    if source_filter:
        query = query.join(Indicator.source).filter(
            Source.name.ilike(f"%{source_filter}%")
        )

    query = query.order_by(Indicator.last_seen.desc().nulls_last()).limit(limit)
    return query.all()


def run_mapping(limit: int, dry_run: bool, source_filter: str | None) -> None:
    logger.info(
        "Démarrage mapping ATT&CK | limit=%d | dry_run=%s | source=%s",
        limit, dry_run, source_filter or "all",
    )

    from enrichment.attack import map_indicator

    with SessionLocal() as session:        
        candidates = get_candidates(session, limit, source_filter)
        logger.info("%d indicateurs candidats", len(candidates))

        if dry_run:
            # Aperçu sans persister
            from enrichment.attack import (
                _load_index, _heuristic_tags,
                _heuristic_source, _heuristic_ioc_type, _deduplicate,
            )
            index = _load_index()
            shown = 0
            for ind in candidates:
                candidates_map = []
                candidates_map.extend(_heuristic_tags(ind, index))
                candidates_map.extend(_heuristic_source(ind, index))
                candidates_map.extend(_heuristic_ioc_type(ind, index))
                candidates_map = _deduplicate(candidates_map)
                if candidates_map:
                    tags = [t.name for t in (ind.tags or [])]
                    source = ind.source.name if ind.source else "?"
                    logger.info(
                        "  [DRY-RUN] %s | %s | tags=%s | source=%s → %s",
                        ind.type.value, ind.value[:40],
                        tags, source,
                        [(t, c) for t, c in candidates_map],
                    )
                    shown += 1
                    if shown >= 20:
                        logger.info("  ... (affichage limité à 20)")
                        break
            return

        mapped = 0
        skipped = 0
        total_techniques = 0

        for i, indicator in enumerate(candidates, 1):
            try:
                results = map_indicator(session, indicator)
                if results:
                    mapped += 1
                    total_techniques += len(results)
                else:
                    skipped += 1
            except Exception as exc:
                logger.error("Erreur pour %s : %s", indicator.value, exc)
                skipped += 1

            if i % 100 == 0:
                logger.info(
                    "Progression : %d/%d | mappés=%d | ignorés=%d",
                    i, len(candidates), mapped, skipped,
                )

        logger.info(
            "Terminé | mappés=%d | ignorés=%d | techniques créées=%d",
            mapped, skipped, total_techniques,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Mapping ATT&CK sur les indicateurs")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--source", type=str, default=None,
                        help="Filtrer par nom de source (ex: openphish)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_mapping(args.limit, args.dry_run, args.source)


if __name__ == "__main__":
    main()