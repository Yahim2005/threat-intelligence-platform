# scripts/backfill_score_breakdown.py
from __future__ import annotations
import sys
import json
from app.database import SessionLocal
from app.models import Indicator
from app.models.enums import IndicatorStatus
from core.scoring import (
    _compute_source_reliability,
    _compute_corroboration,
    _compute_source_diversity,
    _compute_type_bonus,
    _compute_recency,
    _compute_malware_tag_bonus,
    _compute_external_reputation,
    W_SOURCE, W_CORROBORATION, W_DIVERSITY, W_TYPE, W_RECENCY, W_MALWARE_TAG, W_REPUTATION,
)
from sqlalchemy import text

def run():
    session = SessionLocal()

    total = (
        session.query(Indicator)
        .filter(Indicator.status == IndicatorStatus.active)
        .count()
    )
    print(f"[score backfill] {total} IOCs actifs à recalculer…")

    batch_size = 200
    offset = 0
    done = 0
    errors = 0

    while True:
        batch = (
            session.query(Indicator)
            .filter(Indicator.status == IndicatorStatus.active)
            .order_by(Indicator.id)
            .offset(offset)
            .limit(batch_size)
            .all()
        )
        if not batch:
            break

        updates = []
        for ind in batch:
            try:
                source_rel    = _compute_source_reliability(ind)
                corroboration = _compute_corroboration(ind, session)
                diversity     = _compute_source_diversity(ind, session)
                type_bonus    = _compute_type_bonus(ind)
                recency       = _compute_recency(ind)
                malware_tag   = _compute_malware_tag_bonus(ind)
                reputation    = _compute_external_reputation(ind, session)

                raw_score = (
                    W_SOURCE        * source_rel
                    + W_CORROBORATION * corroboration
                    + W_DIVERSITY     * diversity
                    + W_TYPE          * type_bonus
                    + W_RECENCY       * recency
                    + W_MALWARE_TAG   * malware_tag
                    + W_REPUTATION    * reputation
                )
                score = max(0, min(100, round(raw_score * 100)))

                components = {
                    "source_reliability":  round(source_rel, 4),
                    "corroboration":       round(corroboration, 4),
                    "source_diversity":    round(diversity, 4),
                    "type_bonus":          round(type_bonus, 4),
                    "recency":             round(recency, 4),
                    "malware_tag_bonus":   round(malware_tag, 4),
                    "external_reputation": round(reputation, 4),
                }

                updates.append({
                    "id":         str(ind.id),
                    "score":      score,
                    "components": json.dumps(components),
                })
                done += 1
            except Exception as e:
                errors += 1

        # Mise à jour en masse via SQL direct
        for u in updates:
            session.execute(
                text("""
                    UPDATE indicators
                    SET confidence   = :score,
                        raw_metadata = COALESCE(raw_metadata, '{}'::jsonb)
                                    || jsonb_build_object('score_components', cast(:components as jsonb))
                    WHERE id = cast(:id as uuid)
                """),
                {"score": u["score"], "components": u["components"], "id": u["id"]}
            )

        session.commit()
        offset += batch_size
        print(f"  {done}/{total} recalculés, {errors} erreurs…", end="\r")
        sys.stdout.flush()

    session.close()
    print(f"\n[score backfill] Terminé — {done} recalculés, {errors} erreurs.")

if __name__ == "__main__":
    run()