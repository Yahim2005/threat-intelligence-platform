"""
Tests du moteur de scoring de confiance.
On vérifie la cohérence des scores sur des scénarios contrastés,
sans toucher à la vraie base de données.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.enums import IOCType, IndicatorStatus, TLPLevel
from app.models.indicator import Indicator
from app.models.reputation import ReputationCache
from app.models.source import Source
from core.scoring import (
    compute_confidence,
    _compute_source_reliability,
    _compute_corroboration,
    _compute_external_reputation,
    _compute_recency,
    DECAY_DAYS,
    RECENCY_FLOOR,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_source(name: str) -> Source:
    s = Source()
    s.id = uuid.uuid4()
    s.name = name
    return s


def make_indicator(
    ioc_type: str = "ip",
    value: str = "1.2.3.4",
    source_name: str | None = None,
    last_seen_days_ago: int = 1,
) -> Indicator:
    ind = Indicator()
    ind.id = uuid.uuid4()
    ind.value = value
    ind.type = IOCType(ioc_type)
    ind.tlp = TLPLevel.CLEAR
    ind.confidence = 50
    ind.status = IndicatorStatus.active
    ind.tags = []
    ind.raw_metadata = {}
    ind.source = make_source(source_name) if source_name else None
    ind.last_seen = datetime.now(timezone.utc) - timedelta(days=last_seen_days_ago)
    ind.first_seen = ind.last_seen
    return ind


def make_reputation(
    indicator_id,
    source: str,
    abuse_score: int | None = None,
    vt_malicious: int | None = None,
    vt_total: int | None = None,
) -> ReputationCache:
    r = ReputationCache()
    r.id = uuid.uuid4()
    r.indicator_id = indicator_id
    r.source = source
    r.fetched_at = datetime.now(timezone.utc)
    r.error = None
    r.abuse_confidence_score = abuse_score
    r.vt_malicious = vt_malicious
    r.vt_total = vt_total
    return r


def make_session(sighting_count: int = 0, reputations: list = None) -> MagicMock:
    """Session mockée qui retourne un nombre de sightings et des réputations."""
    session = MagicMock()

    # Mock pour _compute_corroboration : session.query(Sighting).filter_by().count()
    sighting_query = MagicMock()
    sighting_query.filter_by.return_value.count.return_value = sighting_count

    # Mock pour _compute_external_reputation : session.query(ReputationCache).filter_by().filter().all()
    reputation_query = MagicMock()
    reputation_query.filter_by.return_value.filter.return_value.all.return_value = (
        reputations or []
    )

    def query_side_effect(model):
        from app.models.sighting import Sighting
        if model is Sighting:
            return sighting_query
        return reputation_query

    session.query.side_effect = query_side_effect
    return session


# ---------------------------------------------------------------------------
# Tests composante par composante
# ---------------------------------------------------------------------------

class TestSourceReliability:

    def test_cisa_is_maximum(self):
        ind = make_indicator(source_name="cisa_kev")
        assert _compute_source_reliability(ind) == 1.0

    def test_openphish_is_high(self):
        ind = make_indicator(source_name="OpenPhish")
        assert _compute_source_reliability(ind) >= 0.7

    def test_unknown_source_is_neutral(self):
        ind = make_indicator(source_name="some_unknown_feed")
        assert _compute_source_reliability(ind) == 0.5

    def test_no_source_is_neutral(self):
        ind = make_indicator(source_name=None)
        assert _compute_source_reliability(ind) == 0.5


class TestCorroboration:

    def test_no_sightings_is_low(self):
        ind = make_indicator()
        session = make_session(sighting_count=0)
        assert _compute_corroboration(ind, session) == 0.1

    def test_one_sighting(self):
        ind = make_indicator()
        session = make_session(sighting_count=1)
        assert _compute_corroboration(ind, session) == 0.2

    def test_five_sightings_is_maximum(self):
        ind = make_indicator()
        session = make_session(sighting_count=5)
        assert _compute_corroboration(ind, session) == 1.0

    def test_more_sightings_does_not_exceed_max(self):
        ind = make_indicator()
        session = make_session(sighting_count=100)
        assert _compute_corroboration(ind, session) == 1.0


class TestExternalReputation:

    def test_no_reputation_is_neutral(self):
        ind = make_indicator()
        session = make_session(reputations=[])
        assert _compute_external_reputation(ind, session) == 0.5

    def test_abuseipdb_score_100(self):
        ind = make_indicator()
        rep = make_reputation(ind.id, "abuseipdb", abuse_score=100)
        session = make_session(reputations=[rep])
        assert _compute_external_reputation(ind, session) == 1.0

    def test_abuseipdb_score_0(self):
        ind = make_indicator()
        rep = make_reputation(ind.id, "abuseipdb", abuse_score=0)
        session = make_session(reputations=[rep])
        assert _compute_external_reputation(ind, session) == 0.0

    def test_virustotal_ratio(self):
        ind = make_indicator()
        rep = make_reputation(ind.id, "virustotal", vt_malicious=36, vt_total=72)
        session = make_session(reputations=[rep])
        assert _compute_external_reputation(ind, session) == pytest.approx(0.5)

    def test_both_sources_averaged(self):
        ind = make_indicator()
        rep1 = make_reputation(ind.id, "abuseipdb", abuse_score=80)   # → 0.8
        rep2 = make_reputation(ind.id, "virustotal", vt_malicious=60, vt_total=80)  # → 0.75
        session = make_session(reputations=[rep1, rep2])
        result = _compute_external_reputation(ind, session)
        assert result == pytest.approx(0.775)


class TestRecency:

    def test_today_is_maximum(self):
        ind = make_indicator(last_seen_days_ago=0)
        assert _compute_recency(ind) == 1.0

    def test_old_indicator_is_floor(self):
        ind = make_indicator(last_seen_days_ago=DECAY_DAYS + 10)
        assert _compute_recency(ind) == RECENCY_FLOOR

    def test_no_last_seen_is_floor(self):
        ind = make_indicator()
        ind.last_seen = None
        assert _compute_recency(ind) == RECENCY_FLOOR

    def test_decay_is_between_bounds(self):
        ind = make_indicator(last_seen_days_ago=45)
        score = _compute_recency(ind)
        assert RECENCY_FLOOR < score < 1.0


# ---------------------------------------------------------------------------
# Tests de cohérence globale (scénarios)
# ---------------------------------------------------------------------------

class TestScenarios:

    def test_strong_indicator_scores_high(self):
        """
        Scénario : IOC vu par CISA (A), 5 sightings, AbuseIPDB=90, vu hier.
        Attendu : score élevé (> 80).
        """
        ind = make_indicator(source_name="cisa_kev", last_seen_days_ago=1)
        rep = make_reputation(ind.id, "abuseipdb", abuse_score=90)
        session = make_session(sighting_count=5, reputations=[rep])
        result = compute_confidence(ind, session)
        assert result["score"] > 80

    def test_weak_indicator_scores_low(self):
        """
        Scénario : IOC sans source connue, 0 sighting, pas de réputation, vu il y a 60 jours.
        Attendu : score faible (< 50).
        """
        ind = make_indicator(source_name=None, last_seen_days_ago=60)
        session = make_session(sighting_count=0, reputations=[])
        result = compute_confidence(ind, session)
        assert result["score"] < 50

    def test_strong_beats_weak(self):
        """
        Un IOC fort doit toujours scorer plus haut qu'un IOC faible.
        """
        ind_strong = make_indicator(source_name="cisa_kev", last_seen_days_ago=1)
        rep_strong = make_reputation(ind_strong.id, "abuseipdb", abuse_score=95)
        session_strong = make_session(sighting_count=5, reputations=[rep_strong])
        score_strong = compute_confidence(ind_strong, session_strong)["score"]

        ind_weak = make_indicator(source_name=None, last_seen_days_ago=60)
        session_weak = make_session(sighting_count=0, reputations=[])
        score_weak = compute_confidence(ind_weak, session_weak)["score"]

        assert score_strong > score_weak

    def test_score_stored_in_metadata(self):
        """
        Les composantes doivent être stockées dans raw_metadata['score_components'].
        """
        ind = make_indicator(source_name="cisa_kev", last_seen_days_ago=1)
        session = make_session(sighting_count=2, reputations=[])
        compute_confidence(ind, session)
        assert "score_components" in ind.raw_metadata
        components = ind.raw_metadata["score_components"]
        assert "source_reliability" in components
        assert "corroboration" in components
        assert "external_reputation" in components
        assert "recency" in components

    def test_confidence_field_updated(self):
        """
        indicator.confidence doit être mis à jour après compute_confidence().
        """
        ind = make_indicator(source_name="cisa_kev", last_seen_days_ago=1)
        ind.confidence = 50  # valeur par défaut
        session = make_session(sighting_count=3, reputations=[])
        result = compute_confidence(ind, session)
        assert ind.confidence == result["score"]
        assert ind.confidence != 50  # a bien été mis à jour