"""Tests d'intégration bout-en-bout : normalisation → persistance → DB.

Ces tests utilisent une vraie base PostgreSQL (tip_test) via les fixtures
du conftest.py. Chaque test est isolé par rollback automatique.
"""
import pytest
from datetime import datetime

from app.models import Indicator, Sighting
from app.models.enums import IOCType, IndicatorStatus, TLPLevel
from app.persistence import get_or_create_indicator, store_records
from core.normalize import detect_and_normalize
from core.quality import check_quality

pytestmark = pytest.mark.integration


# ── Normalisation → persistance ───────────────────────────────────────────────

def test_ip_indicator_created_active(db_session, test_source):
    """Une IP publique malveillante doit être créée avec status=active."""
    indicator, created = get_or_create_indicator(
        db_session, "185.220.101.47", IOCType.ip, test_source.id
    )
    db_session.flush()

    assert created is True
    assert indicator.status == IndicatorStatus.active
    assert indicator.tlp == TLPLevel.CLEAR
    assert indicator.value == "185.220.101.47"
    assert indicator.type == IOCType.ip


def test_private_ip_created_whitelisted(db_session, test_source):
    """Une IP privée RFC1918 doit être créée avec status=whitelisted."""
    indicator, created = get_or_create_indicator(
        db_session, "10.0.0.1", IOCType.ip, test_source.id
    )
    db_session.flush()

    assert created is True
    assert indicator.status == IndicatorStatus.whitelisted
    assert indicator.raw_metadata["quality_reason"] == "private_ip_rfc1918"


def test_public_dns_created_whitelisted(db_session, test_source):
    """8.8.8.8 doit être whitelisté (DNS public connu)."""
    indicator, created = get_or_create_indicator(
        db_session, "8.8.8.8", IOCType.ip, test_source.id
    )
    db_session.flush()

    assert indicator.status == IndicatorStatus.whitelisted
    assert indicator.raw_metadata["quality_reason"] == "known_public_dns"


def test_tranco_domain_created_whitelisted(db_session, test_source):
    """Un domaine Tranco top-10k doit être whitelisté."""
    indicator, created = get_or_create_indicator(
        db_session, "google.com", IOCType.domain, test_source.id
    )
    db_session.flush()

    assert indicator.status == IndicatorStatus.whitelisted
    assert indicator.raw_metadata["quality_reason"] == "tranco_top10k"


def test_get_or_create_idempotent(db_session, test_source):
    """Appeler get_or_create_indicator deux fois sur le même IOC
    ne doit créer qu'un seul Indicator."""
    ind1, created1 = get_or_create_indicator(
        db_session, "185.220.101.47", IOCType.ip, test_source.id
    )
    db_session.flush()

    ind2, created2 = get_or_create_indicator(
        db_session, "185.220.101.47", IOCType.ip, test_source.id
    )
    db_session.flush()

    assert created1 is True
    assert created2 is False
    assert ind1.id == ind2.id


def test_store_records_full_pipeline(db_session, test_source):
    """store_records doit créer des Indicators + Sightings en base."""
    records = [
        {
            "value": "194.61.24.102",
            "type": IOCType.ip,
            "seen_at": datetime(2026, 6, 1, 12, 0, 0),
            "metadata": {"source": "test"},
            "tag_names": ["kind:c2"],
            "context": {"port": 443},
        },
        {
            "value": "evil-test-domain.com",
            "type": IOCType.domain,
            "seen_at": datetime(2026, 6, 1, 12, 0, 0),
            "metadata": {},
            "tag_names": ["kind:phishing"],
            "context": {},
        },
    ]

    stats = store_records(records, "Test Source", db_session)

    assert stats["created"] == 2
    assert stats["updated"] == 0
    assert stats["sightings"] == 2
    assert stats["errors"] == 0

    indicators = db_session.query(Indicator).filter(
        Indicator.value.in_(["194.61.24.102", "evil-test-domain.com"])
    ).all()
    assert len(indicators) == 2

    indicator_ids = [indicator.id for indicator in indicators]
    sightings = db_session.query(Sighting).filter(
        Sighting.indicator_id.in_(indicator_ids)
    ).all()
    assert len(sightings) == 2


def test_store_records_tlp_inherited_from_source(db_session):
    """L'Indicator doit hériter du TLP de sa Source."""
    from app.models import Source
    green_source = Source(
        name="Green Source",
        url="https://example.com",
        source_type=__import__('app.models.enums', fromlist=['SourceType']).SourceType.feed,
        tlp=TLPLevel.GREEN,
        is_active=True,
    )
    db_session.add(green_source)
    db_session.flush()

    indicator, created = get_or_create_indicator(
        db_session, "91.219.236.18", IOCType.ip, green_source.id,
        tlp=green_source.tlp
    )
    db_session.flush()

    assert indicator.tlp == TLPLevel.GREEN


def test_normalize_then_persist(db_session, test_source):
    """detect_and_normalize + get_or_create_indicator : pipeline complet."""
    raw_value = "hxxp://evil[.]example[.]com/payload"
    result = detect_and_normalize(raw_value)
    assert result is not None

    value, ioc_type = result
    assert ioc_type == IOCType.url

    indicator, created = get_or_create_indicator(
        db_session, value, ioc_type, test_source.id
    )
    db_session.flush()

    assert created is True
    assert indicator.value == value
    assert indicator.type == IOCType.url


# ── Performance ───────────────────────────────────────────────────────────────

def test_search_by_value_uses_index(test_engine):
    """Vérifie que la recherche par value utilise bien l'index (pas de seq scan)."""
    with test_engine.connect() as conn:
        result = conn.execute(
            __import__('sqlalchemy', fromlist=['text']).text(
                "EXPLAIN SELECT * FROM indicators WHERE value = '185.220.101.47'"
            )
        ).fetchall()

    plan = " ".join(row[0] for row in result)
    assert "Index" in plan or "index" in plan, f"Seq scan détecté : {plan}"
