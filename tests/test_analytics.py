# tests/test_analytics.py

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.database import SessionLocal
from app.models import Indicator, Source, Tag
from app.models.enums import IOCType, IndicatorStatus, TLPLevel, RelationshipType
from app.models.relationship import TIPRelationship
from app.models.sighting import Sighting


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def source(db):
    src = Source(
        id=uuid4(),
        name=f"test-source-{uuid4().hex[:6]}",
        url="https://test.example.com",
        tlp=TLPLevel.CLEAR,
        is_active=True,
    )
    db.add(src)
    db.flush()
    return src


@pytest.fixture()
def indicator_pair(db, source):
    """Crée deux indicateurs liés par une relation."""
    ind_a = Indicator(
        id=uuid4(),
        value=f"192.0.2.{uuid4().hex[:2]}",
        type=IOCType.ip,
        status=IndicatorStatus.active,
        confidence=70,
        tlp=TLPLevel.CLEAR,
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        source_id=source.id,
    )
    ind_b = Indicator(
        id=uuid4(),
        value=f"evil-{uuid4().hex[:6]}.example.com",
        type=IOCType.domain,
        status=IndicatorStatus.active,
        confidence=60,
        tlp=TLPLevel.CLEAR,
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        source_id=source.id,
    )
    db.add_all([ind_a, ind_b])
    db.flush()

    rel = TIPRelationship(
        id=uuid4(),
        source_ref=str(ind_a.id),
        target_ref=str(ind_b.id),
        relationship_type=RelationshipType.resolves_to,
        confidence=90,
        rule="test_rule",
    )
    db.add(rel)
    db.flush()

    return ind_a, ind_b


@pytest.fixture()
def indicator_with_sightings(db, source):
    """Crée un indicateur avec des sightings sur 3 jours distincts."""
    ind = Indicator(
        id=uuid4(),
        value=f"hash-{uuid4().hex}",
        type=IOCType.md5,
        status=IndicatorStatus.active,
        confidence=80,
        tlp=TLPLevel.CLEAR,
        first_seen=datetime.utcnow() - timedelta(days=5),
        last_seen=datetime.utcnow(),
        source_id=source.id,
    )
    db.add(ind)
    db.flush()

    for days_ago in [3, 2, 1]:
        sighting = Sighting(
            id=uuid4(),
            indicator_id=ind.id,
            seen_at=datetime.utcnow() - timedelta(days=days_ago),
            count=days_ago * 2,
        )
        db.add(sighting)
    db.flush()

    return ind


# ─── Tests : /related ────────────────────────────────────────────────────────

def test_related_returns_linked_indicator(db, indicator_pair):
    from api.queries import get_related_indicators
    ind_a, ind_b = indicator_pair

    results = get_related_indicators(db, ind_a.value)

    assert len(results) == 1
    assert results[0]["value"] == ind_b.value
    assert results[0]["relationship_type"] == "resolves_to"
    assert results[0]["relationship_confidence"] == 90


def test_related_works_from_both_directions(db, indicator_pair):
    from api.queries import get_related_indicators
    ind_a, ind_b = indicator_pair

    # ind_b est la cible — il doit aussi trouver ind_a
    results = get_related_indicators(db, ind_b.value)

    assert len(results) == 1
    assert results[0]["value"] == ind_a.value


def test_related_returns_empty_for_unknown_value(db):
    from api.queries import get_related_indicators

    results = get_related_indicators(db, "value-that-does-not-exist")
    assert results == []


# ─── Tests : /timeline ───────────────────────────────────────────────────────

def test_timeline_returns_sightings_by_day(db, indicator_with_sightings):
    from api.queries import get_indicator_timeline
    ind = indicator_with_sightings

    results = get_indicator_timeline(db, ind.value, days=30)

    assert len(results) == 3
    # Vérifie que chaque entrée a les bons champs
    for point in results:
        assert "date" in point
        assert "sightings" in point
        assert point["sightings"] > 0


def test_timeline_returns_empty_for_unknown_value(db):
    from api.queries import get_indicator_timeline

    results = get_indicator_timeline(db, "unknown-value-xyz")
    assert results == []


# ─── Tests : /stats/trends ───────────────────────────────────────────────────

def test_trends_returns_list(db):
    from api.queries import get_ingestion_trends

    results = get_ingestion_trends(db, days=30)

    # Doit être une liste (potentiellement vide si aucun IOC récent)
    assert isinstance(results, list)
    for point in results:
        assert "date" in point
        assert "count" in point
        assert point["count"] > 0