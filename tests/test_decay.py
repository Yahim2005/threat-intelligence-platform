"""
Tests du moteur de décroissance temporelle (decay).

Scénarios clés :
- IOC récent → pas de decay significatif
- IOC ancien → expiré
- IOC revu (wake_up) → réactivé
- Demi-vies différentes selon le type
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.enums import IOCType, IndicatorStatus, TLPLevel
from app.models.indicator import Indicator
from app.models.source import Source
from core.decay import (
    compute_decay_factor,
    compute_age_days,
    apply_decay,
    wake_up,
    get_half_life,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_indicator(
    ioc_type: str = "url",
    value: str = "http://evil.com",
    source_name: str | None = "openphish",
    last_seen_days_ago: int = 1,
    status: IndicatorStatus = IndicatorStatus.active,
) -> Indicator:
    ind = Indicator()
    ind.id = uuid.uuid4()
    ind.value = value
    ind.type = IOCType(ioc_type)
    ind.tlp = TLPLevel.CLEAR
    ind.confidence = 50
    ind.status = status
    ind.tags = []
    ind.raw_metadata = {}
    ind.last_seen = datetime.now(timezone.utc) - timedelta(days=last_seen_days_ago)
    ind.first_seen = ind.last_seen
    if source_name:
        s = Source()
        s.id = uuid.uuid4()
        s.name = source_name
        ind.source = s
    else:
        ind.source = None
    return ind


def make_session(sighting_count: int = 1) -> MagicMock:
    session = MagicMock()
    sighting_q = MagicMock()
    sighting_q.filter_by.return_value.count.return_value = sighting_count
    reputation_q = MagicMock()
    reputation_q.filter_by.return_value.filter.return_value.all.return_value = []

    def query_side(model):
        from app.models.sighting import Sighting
        if model is Sighting:
            return sighting_q
        return reputation_q

    session.query.side_effect = query_side
    return session


# ---------------------------------------------------------------------------
# Tests compute_decay_factor
# ---------------------------------------------------------------------------

class TestDecayFactor:

    def test_age_zero_is_one(self):
        """Aucune décroissance le jour J."""
        assert compute_decay_factor("url", 0) == 1.0

    def test_half_life_gives_half(self):
        """À t = demi-vie, le facteur doit être ≈ 0.5."""
        half_life = get_half_life("url")  # 7 jours
        factor = compute_decay_factor("url", half_life)
        assert abs(factor - 0.5) < 0.01

    def test_two_half_lives_gives_quarter(self):
        """À t = 2 × demi-vie, le facteur doit être ≈ 0.25."""
        half_life = get_half_life("url")
        factor = compute_decay_factor("url", half_life * 2)
        assert abs(factor - 0.25) < 0.01

    def test_floor_at_minimum(self):
        """Le facteur ne descend jamais sous 0.01."""
        factor = compute_decay_factor("url", 10000)
        assert factor == 0.01

    def test_hash_decays_slower_than_url(self):
        """Un hash doit décroître beaucoup plus lentement qu'une URL."""
        age = 30  # 30 jours
        factor_url = compute_decay_factor("url", age)
        factor_hash = compute_decay_factor("sha256", age)
        assert factor_hash > factor_url

    def test_different_types_have_different_half_lives(self):
        assert get_half_life("url") < get_half_life("ip")
        assert get_half_life("ip") < get_half_life("sha256")


# ---------------------------------------------------------------------------
# Tests apply_decay
# ---------------------------------------------------------------------------

class TestApplyDecay:

    def test_recent_indicator_stays_active(self):
        """Un IOC vu hier ne doit pas expirer."""
        ind = make_indicator(ioc_type="ip", last_seen_days_ago=1)
        session = make_session(sighting_count=2)
        result = apply_decay(ind, session)
        assert ind.status == IndicatorStatus.active
        assert result["status_changed"] is False

    def test_old_url_expires(self):
        """Une URL très ancienne (>> demi-vie) doit expirer."""
        ind = make_indicator(ioc_type="url", last_seen_days_ago=180)
        session = make_session(sighting_count=1)
        result = apply_decay(ind, session)
        assert ind.status == IndicatorStatus.expired
        assert result["status_changed"] is True

    def test_old_hash_may_stay_active(self):
        """Un hash de 60 jours (< demi-vie 365j) ne doit pas expirer."""
        ind = make_indicator(ioc_type="sha256", last_seen_days_ago=60)
        session = make_session(sighting_count=2)
        result = apply_decay(ind, session)
        # Avec une demi-vie de 365 jours, 60 jours = décroissance modérée
        assert result["decay_factor"] > 0.5
        assert ind.status == IndicatorStatus.active

    def test_decayed_score_lower_than_base(self):
        """Le score avec decay doit être ≤ score de base."""
        ind = make_indicator(ioc_type="url", last_seen_days_ago=30)
        session = make_session(sighting_count=1)
        result = apply_decay(ind, session)
        assert result["decayed_score"] <= result["base_score"]

    def test_metadata_contains_decay_info(self):
        """Les métadonnées doivent contenir les infos de decay."""
        ind = make_indicator(ioc_type="ip", last_seen_days_ago=10)
        session = make_session(sighting_count=1)
        apply_decay(ind, session)
        assert "decay" in ind.raw_metadata
        decay_meta = ind.raw_metadata["decay"]
        assert "age_days" in decay_meta
        assert "half_life" in decay_meta
        assert "decay_factor" in decay_meta
        assert "base_score" in decay_meta
        assert "decayed_score" in decay_meta

    def test_confidence_updated(self):
        """indicator.confidence doit être mis à jour avec le score décaté."""
        ind = make_indicator(ioc_type="url", last_seen_days_ago=30)
        session = make_session(sighting_count=1)
        result = apply_decay(ind, session)
        assert ind.confidence == result["decayed_score"]


# ---------------------------------------------------------------------------
# Tests wake_up
# ---------------------------------------------------------------------------

class TestWakeUp:

    def test_expired_indicator_reactivated(self):
        """Un IOC expiré doit revenir à active après wake_up."""
        ind = make_indicator(
            ioc_type="ip",
            last_seen_days_ago=200,
            status=IndicatorStatus.expired,
        )
        ind.confidence = 5  # score très bas
        session = make_session(sighting_count=3)
        wake_up(ind, session)
        assert ind.status == IndicatorStatus.active

    def test_last_seen_updated(self):
        """last_seen doit être mis à jour à maintenant."""
        ind = make_indicator(last_seen_days_ago=100)
        session = make_session(sighting_count=1)
        before = datetime.now(timezone.utc)
        wake_up(ind, session)
        assert ind.last_seen >= before

    def test_decay_metadata_cleared(self):
        """Les métadonnées de decay obsolètes doivent être supprimées."""
        ind = make_indicator(last_seen_days_ago=100)
        ind.raw_metadata = {"decay": {"age_days": 100, "decay_factor": 0.01}}
        session = make_session(sighting_count=2)
        wake_up(ind, session)
        assert "decay" not in ind.raw_metadata

    def test_score_recalculated_after_wakeup(self):
        """Après wake_up, le score doit être recalculé (pas zéro)."""
        ind = make_indicator(
            ioc_type="ip",
            source_name="cisa_kev",
            last_seen_days_ago=200,
            status=IndicatorStatus.expired,
        )
        ind.confidence = 5
        session = make_session(sighting_count=3)
        wake_up(ind, session)
        assert ind.confidence > 5

    def test_session_committed(self):
        """wake_up doit commiter la session."""
        ind = make_indicator(last_seen_days_ago=50)
        session = make_session(sighting_count=1)
        wake_up(ind, session)
        session.commit.assert_called()