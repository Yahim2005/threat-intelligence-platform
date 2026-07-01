# scripts/backfill_geoip.py
"""
Enrichit toutes les IPs actives en base avec GeoIP + ASN.
Lance avec : python -m scripts.backfill_geoip
"""
from __future__ import annotations
import sys
from app.database import SessionLocal
from app.models import Indicator
from app.models.enums import IOCType, IndicatorStatus
from enrichment.geoip import GeoIPEnricher
from app.models.enrichment import Enrichment
from datetime import datetime

def run():
    session = SessionLocal()
    enricher = GeoIPEnricher()

    # Compte total des IPs actives
    total = (
        session.query(Indicator)
        .filter(Indicator.type.in_([IOCType.ip, IOCType.ipv6]))
        .filter(Indicator.status == IndicatorStatus.active)
        .count()
    )
    print(f"[geoip backfill] {total} IPs à enrichir…")

    batch_size = 500
    offset = 0
    done = 0
    errors = 0

    while True:
        batch = (
            session.query(Indicator)
            .filter(Indicator.type.in_([IOCType.ip, IOCType.ipv6]))
            .filter(Indicator.status == IndicatorStatus.active)
            .order_by(Indicator.id)
            .offset(offset)
            .limit(batch_size)
            .all()
        )
        if not batch:
            break

        for ind in batch:
            try:
                data = enricher.enrich(ind)
                if not data:
                    done += 1
                    continue

                existing = (
                    session.query(Enrichment)
                    .filter_by(indicator_id=ind.id, provider="geoip")
                    .first()
                )
                if existing:
                    existing.data = data
                    existing.enriched_at = datetime.utcnow()
                else:
                    session.add(Enrichment(
                        indicator_id=ind.id,
                        provider="geoip",
                        data=data,
                        enriched_at=datetime.utcnow(),
                    ))
                done += 1
            except Exception as e:
                errors += 1

        session.commit()
        offset += batch_size
        print(f"  {done}/{total} enrichis, {errors} erreurs…", end="\r")
        sys.stdout.flush()

    session.close()
    print(f"\n[geoip backfill] Terminé — {done} enrichis, {errors} erreurs.")

if __name__ == "__main__":
    run()