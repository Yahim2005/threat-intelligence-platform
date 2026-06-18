"""Tests J11 — déduplication, fusion, et gestion de concurrence.
Aucun mock : utilise une vraie session DB pour tester le comportement
transactionnel (upsert, races conditions).
"""
import pytest


TEST_VALUES = [
    "203.0.113.200", "203.0.113.201", "203.0.113.202", "203.0.113.203",
    "203.0.113.204", "203.0.113.205", "203.0.113.206",
]


@pytest.fixture(autouse=True)
def clean_test_indicators():
    """Supprime les indicateurs de test avant chaque test, pour garantir
    l'idempotence : ces tests doivent pouvoir être rejoués indéfiniment
    sans dépendre de l'état laissé par une exécution précédente."""
    session = SessionLocal()
    try:
        session.query(Indicator).filter(Indicator.value.in_(TEST_VALUES)).delete(
            synchronize_session=False
        )
        session.commit()
    finally:
        session.close()
    yield
import threading
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import Indicator
from app.models.enums import IOCType
from app.persistence import store_records


# ── Déduplication multi-sources (critère DoD explicite du roadmap) ───────────
def test_same_ip_from_three_sources_yields_one_indicator_three_sightings():
    """La même IP observée par 3 sources différentes = 1 Indicator + 3 Sightings."""
    value = "203.0.113.200"
    session = SessionLocal()
    try:
        store_records([{"value": value, "type": IOCType.ip}], "abuse.ch - Feodo", session)
        store_records([{"value": value, "type": IOCType.ip}], "abuse.ch - ThreatFox", session)
        store_records([{"value": value, "type": IOCType.ip}], "Spamhaus - DROP", session)

        indicators = session.query(Indicator).filter_by(value=value, type=IOCType.ip).all()
        assert len(indicators) == 1

        indicator = indicators[0]
        assert len(indicator.sightings) == 3
    finally:
        session.close()


# ── first_seen / last_seen ────────────────────────────────────────────────────
def test_first_seen_never_moves_forward():
    """Une observation plus ANCIENNE doit reculer first_seen, jamais l'inverse."""
    value = "203.0.113.201"
    session = SessionLocal()
    try:
        recent = datetime(2026, 6, 15)
        older = datetime(2026, 6, 1)

        store_records([{"value": value, "type": IOCType.ip, "seen_at": recent}], "OpenPhish", session)
        store_records([{"value": value, "type": IOCType.ip, "seen_at": older}], "OpenPhish", session)

        indicator = session.query(Indicator).filter_by(value=value, type=IOCType.ip).first()
        assert indicator.first_seen == older
    finally:
        session.close()


def test_last_seen_never_moves_backward():
    """Une observation plus ANCIENNE ne doit jamais reculer last_seen."""
    value = "203.0.113.202"
    session = SessionLocal()
    try:
        recent = datetime(2026, 6, 15)
        older = datetime(2026, 6, 1)

        store_records([{"value": value, "type": IOCType.ip, "seen_at": recent}], "OpenPhish", session)
        store_records([{"value": value, "type": IOCType.ip, "seen_at": older}], "OpenPhish", session)

        indicator = session.query(Indicator).filter_by(value=value, type=IOCType.ip).first()
        assert indicator.last_seen == recent
    finally:
        session.close()


def test_first_and_last_seen_converge_to_widest_range():
    """Sur N observations, first_seen = la plus ancienne, last_seen = la plus récente."""
    value = "203.0.113.203"
    session = SessionLocal()
    try:
        base = datetime(2026, 6, 10)
        dates = [base, base - timedelta(days=5), base + timedelta(days=3), base - timedelta(days=1)]

        for d in dates:
            store_records([{"value": value, "type": IOCType.ip, "seen_at": d}], "OpenPhish", session)

        indicator = session.query(Indicator).filter_by(value=value, type=IOCType.ip).first()
        assert indicator.first_seen == min(dates)
        assert indicator.last_seen == max(dates)
    finally:
        session.close()


# ── Fusion / agrégation ────────────────────────────────────────────────────────
def test_metadata_merges_across_sources_without_overwriting_distinct_keys():
    """Des clés distinctes de deux sources doivent coexister dans raw_metadata."""
    value = "203.0.113.204"
    session = SessionLocal()
    try:
        store_records(
            [{"value": value, "type": IOCType.ip, "metadata": {"malware": "Dridex"}}],
            "abuse.ch - Feodo",
            session,
        )
        store_records(
            [{"value": value, "type": IOCType.ip, "metadata": {"threat_type": "c2"}}],
            "abuse.ch - ThreatFox",
            session,
        )

        indicator = session.query(Indicator).filter_by(value=value, type=IOCType.ip).first()
        assert indicator.raw_metadata["malware"] == "Dridex"
        assert indicator.raw_metadata["threat_type"] == "c2"
    finally:
        session.close()


def test_tags_form_a_union_without_duplicates():
    """Les tags de différentes sources doivent s'additionner sans doublon."""
    value = "203.0.113.205"
    session = SessionLocal()
    try:
        store_records(
            [{"value": value, "type": IOCType.ip, "tag_names": ["c2"]}],
            "abuse.ch - Feodo",
            session,
        )
        store_records(
            [{"value": value, "type": IOCType.ip, "tag_names": ["c2", "botnet"]}],
            "abuse.ch - ThreatFox",
            session,
        )

        indicator = session.query(Indicator).filter_by(value=value, type=IOCType.ip).first()
        tag_names = sorted(t.name for t in indicator.tags)
        assert tag_names == ["botnet", "c2"]
    finally:
        session.close()


# ── Concurrence (le vrai piège du jour, déjà reproduit manuellement) ─────────
def test_concurrent_inserts_of_same_value_yield_one_indicator_no_errors():
    """5 threads créant simultanément le même indicateur : 1 seul créé, 0 erreur,
    les 4 autres doivent le retrouver et créer leur propre Sighting."""
    value = "203.0.113.206"
    results = []

    def worker():
        session = SessionLocal()
        try:
            stats = store_records(
                [{"value": value, "type": IOCType.ip}], "OpenPhish", session
            )
            results.append(stats)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total_errors = sum(r["errors"] for r in results)
    total_created = sum(r["created"] for r in results)
    total_sightings = sum(r["sightings"] for r in results)

    assert total_errors == 0
    assert total_created == 1
    assert total_sightings == 5

    session = SessionLocal()
    try:
        indicators = session.query(Indicator).filter_by(value=value, type=IOCType.ip).all()
        assert len(indicators) == 1
        assert len(indicators[0].sightings) == 5
    finally:
        session.close()