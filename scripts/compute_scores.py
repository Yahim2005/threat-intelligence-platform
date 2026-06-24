#!/usr/bin/env python3
"""
Calcule et met à jour le score de confiance de tous les indicateurs actifs.

Usage:
    python scripts/compute_scores.py --limit 1000 --dry-run
    python scripts/compute_scores.py --limit 5000
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import joinedload

from app.models import Indicator
from app.models.enums import IndicatorStatus
from core.scoring import compute_confidence
from app.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("compute_scores")


def run(limit: int, dry_run: bool) -> None:
    logger.info("Démarrage scoring | limit=%d | dry_run=%s", limit, dry_run)

    with SessionLocal() as session:
        indicators = (
            session.query(Indicator)
            .options(
                joinedload(Indicator.source),
                joinedload(Indicator.tags),
            )
            .filter(Indicator.status == IndicatorStatus.active)
            .order_by(Indicator.last_seen.desc().nulls_last())
            .limit(limit)
            .all()
        )

        logger.info("%d indicateurs à scorer", len(indicators))

        scored = 0
        score_sum = 0

        for i, indicator in enumerate(indicators, 1):
            result = compute_confidence(indicator, session)
            score_sum += result["score"]
            scored += 1

            if dry_run and i <= 10:
                logger.info(
                    "  [DRY-RUN] %s | %s | score=%d | %s",
                    indicator.type.value,
                    indicator.value[:40],
                    result["score"],
                    result["components"],
                )

            if not dry_run:
                if i % 500 == 0:
                    session.commit()
                    logger.info("Progression : %d/%d", i, len(indicators))

        if not dry_run:
            session.commit()
            avg = score_sum / scored if scored else 0
            logger.info(
                "Terminé | scorés=%d | score moyen=%.1f",
                scored, avg,
            )
        else:
            logger.info("[DRY-RUN] %d indicateurs auraient été scorés", scored)


def main() -> None:
    parser = argparse.ArgumentParser(description="Calcul des scores de confiance")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.limit, args.dry_run)


if __name__ == "__main__":
    main()