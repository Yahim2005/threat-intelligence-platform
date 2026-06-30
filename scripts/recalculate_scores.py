"""Recalcule le confidence score de tous les indicateurs actifs avec
l'algorithme de scoring v2 (core/scoring.py).

Usage :
    python -m scripts.recalculate_scores --dry-run     # aperçu, aucune écriture
    python -m scripts.recalculate_scores               # exécution réelle

N'affecte que les indicateurs au statut 'active' — les expirés et
whitelistés ne sont pas recalculés (changer leur score n'a pas de sens
opérationnel).
"""
import argparse
import logging
import time

from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models.indicator import Indicator
from app.models.enums import IndicatorStatus
from core.scoring import compute_confidence

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def recalculate(dry_run: bool = True) -> None:
    session = SessionLocal()
    try:
        total = (
            session.query(Indicator)
            .filter_by(status=IndicatorStatus.active)
            .count()
        )
        print(f"Indicateurs actifs à recalculer : {total}")
        if dry_run:
            print("Mode DRY-RUN — aucune écriture ne sera effectuée.\n")

        distribution_before: dict[int, int] = {}
        distribution_after: dict[int, int] = {}

        processed = 0
        changed = 0
        errors = 0
        start = time.time()

        offset = 0
        while True:
            batch = (
                session.query(Indicator)
                .options(joinedload(Indicator.tags))
                .filter_by(status=IndicatorStatus.active)
                .order_by(Indicator.id)
                .offset(offset)
                .limit(BATCH_SIZE)
                .all()
            )
            if not batch:
                break

            for ind in batch:
                old_score = ind.confidence
                distribution_before[old_score] = distribution_before.get(old_score, 0) + 1
                try:
                    result = compute_confidence(ind, session)
                    new_score = result["score"]
                    distribution_after[new_score] = distribution_after.get(new_score, 0) + 1
                    if new_score != old_score:
                        changed += 1
                    if dry_run:
                        # Annule l'effet de bord de compute_confidence (qui modifie l'objet en mémoire)
                        session.expire(ind)
                except Exception as e:
                    errors += 1
                    logger.error(f"Erreur sur {ind.id} ({ind.value[:50]!r}) : {e}")

                processed += 1
                if processed % 5000 == 0:
                    print(f"  ... {processed}/{total} traités")

            if not dry_run:
                session.commit()
            else:
                session.rollback()

            offset += BATCH_SIZE

        duration = time.time() - start

        print(f"\nTerminé en {duration:.1f}s")
        print(f"  Traités : {processed}")
        print(f"  Modifiés : {changed}")
        print(f"  Erreurs : {errors}")

        def summarize(dist: dict[int, int]) -> str:
            if not dist:
                return "  (vide)"
            avg = sum(score * count for score, count in dist.items()) / sum(dist.values())
            mn, mx = min(dist), max(dist)
            return f"  Moyenne={avg:.1f}  Min={mn}  Max={mx}  Valeurs distinctes={len(dist)}"

        print("\nDistribution AVANT :")
        print(summarize(distribution_before))
        print("\nDistribution APRÈS :")
        print(summarize(distribution_after))

        if dry_run:
            print("\nDRY-RUN terminé — aucune modification persistée.")
            print("Relancer sans --dry-run pour appliquer les changements.")
        else:
            print("\nModifications appliquées et committées.")

    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recalcule les scores de confidence (v2)")
    parser.add_argument("--dry-run", action="store_true", help="Aperçu sans écriture")
    args = parser.parse_args()
    recalculate(dry_run=args.dry_run)
