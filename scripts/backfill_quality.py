"""Script de backfill rétroactif — applique core/quality.py aux indicateurs
déjà en base, créés avant l'introduction du filtre anti-faux-positifs (J12).

Par défaut, tourne en DRY-RUN : affiche les statistiques sans rien modifier.
Utiliser --apply pour committer réellement les changements.

Usage:
    python -m scripts.backfill_quality              # dry-run
    python -m scripts.backfill_quality --apply       # applique pour de vrai
"""
import argparse
import logging
from collections import Counter

from app.database import SessionLocal
from app.models import Indicator
from app.models.enums import IndicatorStatus
from core.quality import check_quality

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 5000


def run(apply: bool) -> None:
    session = SessionLocal()
    reason_counts: Counter[str] = Counter()
    total_scanned = 0
    total_flagged = 0

    try:
        query = (
            session.query(Indicator)
            .filter(Indicator.status == IndicatorStatus.active)
            .yield_per(BATCH_SIZE)
        )

        batch_changes = 0
        for indicator in query:
            total_scanned += 1
            verdict = check_quality(indicator.value, indicator.type)

            if verdict.is_false_positive:
                total_flagged += 1
                reason_counts[verdict.reason] += 1

                if apply:
                    indicator.status = IndicatorStatus.whitelisted
                    indicator.raw_metadata = {
                        **(indicator.raw_metadata or {}),
                        "quality_reason": verdict.reason,
                    }
                    batch_changes += 1

            if apply and batch_changes >= BATCH_SIZE:
                session.commit()
                logger.info(f"Commit intermédiaire — {total_scanned} scannés jusqu'ici")
                batch_changes = 0

        if apply and batch_changes > 0:
            session.commit()

    finally:
        session.close()

    mode = "APPLIQUÉ" if apply else "DRY-RUN (rien modifié)"
    logger.info(f"=== Backfill terminé [{mode}] ===")
    logger.info(f"Total scanné      : {total_scanned}")
    logger.info(f"Total à whiteliste: {total_flagged}")
    for reason, count in reason_counts.most_common():
        logger.info(f"  - {reason:25} : {count}")

    if not apply and total_flagged > 0:
        logger.info("Relance avec --apply pour committer ces changements.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill quality.py sur les indicateurs existants")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applique réellement les changements (sinon dry-run par défaut)",
    )
    args = parser.parse_args()
    run(apply=args.apply)