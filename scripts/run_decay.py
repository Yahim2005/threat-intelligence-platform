#!/usr/bin/env python3
"""
Job quotidien de péremption des indicateurs.

Recalcule le score avec decay pour tous les indicateurs actifs,
et bascule en `expired` ceux qui sont sous le seuil.

Usage:
    python scripts/run_decay.py --dry-run
    python scripts/run_decay.py --limit 5000
    python scripts/run_decay.py  # tous les indicateurs actifs
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
from app.database import SessionLocal
from core.decay import apply_decay, get_expiry_threshold, get_warning_threshold

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("run_decay")


def run(limit: int | None, dry_run: bool) -> None:
    logger.info(
        "Démarrage decay job | limit=%s | dry_run=%s | seuil_expiry=%d | seuil_warning=%d",
        limit or "all", dry_run,
        get_expiry_threshold(), get_warning_threshold(),
    )

    session = SessionLocal()
    try:
        query = (
            session.query(Indicator)
            .options(
                joinedload(Indicator.source),
                joinedload(Indicator.tags),
            )
            .filter(Indicator.status == IndicatorStatus.active)
            .order_by(Indicator.last_seen.asc().nulls_first())  # les plus vieux d'abord
        )
        if limit:
            query = query.limit(limit)

        indicators = query.all()
        logger.info("%d indicateurs actifs à traiter", len(indicators))

        stats = {
            "processed": 0,
            "expired":   0,
            "warned":    0,
            "unchanged": 0,
        }

        for i, indicator in enumerate(indicators, 1):
            result = apply_decay(indicator, session)
            stats["processed"] += 1

            if result["status_changed"]:
                stats["expired"] += 1
            elif result["decayed_score"] < get_warning_threshold():
                stats["warned"] += 1
            else:
                stats["unchanged"] += 1

            if dry_run and i <= 15:
                logger.info(
                    "  [DRY-RUN] %s | %s | age=%.0fd | t½=%dd | "
                    "score %d → %d (×%.3f) | statut=%s%s",
                    indicator.type.value,
                    indicator.value[:40],
                    result["age_days"],
                    result["half_life"],
                    result["base_score"],
                    result["decayed_score"],
                    result["decay_factor"],
                    result["status"],
                    " ← EXPIRÉ" if result["status_changed"] else "",
                )

            if not dry_run and i % 500 == 0:
                session.commit()
                logger.info("Progression : %d/%d", i, len(indicators))

        if not dry_run:
            session.commit()

        logger.info(
            "Terminé | traités=%d | expirés=%d | en warning=%d | inchangés=%d",
            stats["processed"], stats["expired"],
            stats["warned"], stats["unchanged"],
        )

    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Job de péremption des indicateurs")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Nombre max d'indicateurs à traiter (défaut: tous)"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.limit, args.dry_run)


if __name__ == "__main__":
    main()