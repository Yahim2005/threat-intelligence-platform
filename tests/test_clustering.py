"""Tests du clustering actuel par institution camerounaise ciblee."""
from __future__ import annotations

from collections import Counter
from unittest.mock import MagicMock
from uuid import uuid4

from app.models.enums import AssetCategory, ThreatType, TLPLevel
from app.models.indicator import Indicator
from app.models.monitored_asset import MonitoredAsset
from app.models.tag import Tag
from app.models.threat import Threat
from core.clustering import (
    _build_description,
    _build_name,
    _resolve_institution,
    _slugify,
    _upsert_threat,
    get_threats_for_indicator,
    mechanism_counts_for_indicators,
)


def make_asset(name: str = "Ministere des Finances", acronym: str = "MINFI") -> MonitoredAsset:
    asset = MonitoredAsset()
    asset.id = uuid4()
    asset.name = name
    asset.acronym = acronym
    asset.category = AssetCategory.ministry
    return asset


def make_indicator(*tag_names: str) -> Indicator:
    indicator = Indicator()
    indicator.id = uuid4()
    indicator.value = f"ioc-{uuid4().hex}.example"
    indicator.tags = [Tag(id=uuid4(), name=name) for name in tag_names]
    indicator.threats = []
    return indicator


def test_slugify_prefers_acronym():
    assert _slugify(make_asset()) == "minfi"


def test_resolve_institution_collects_mechanisms():
    asset = make_asset()
    indicator = make_indicator("typosquat:minfi", "ct:minfi", "malware:test")

    resolved = _resolve_institution(indicator, {"minfi": asset})

    assert resolved is not None
    resolved_asset, mechanisms = resolved
    assert resolved_asset is asset
    assert mechanisms == {"typosquat", "ct"}


def test_resolve_institution_ignores_unknown_tags():
    asset = make_asset()
    indicator = make_indicator("malware:emotet", "typosquat:unknown")
    assert _resolve_institution(indicator, {"minfi": asset}) is None


def test_mechanism_counts_counts_each_mechanism_once_per_indicator():
    indicators = [
        make_indicator("typosquat:minfi", "ct:minfi"),
        make_indicator("typosquat:minfi", "typosquat:other"),
    ]
    assert mechanism_counts_for_indicators(indicators) == Counter(
        {"typosquat": 2, "ct": 1}
    )


def test_build_name_is_deterministic():
    asset = make_asset()
    assert _build_name(asset, {"ct", "typosquat"}, True) == (
        "Ministere des Finances — typosquatting + certificats suspects + surface d'attaque"
    )


def test_build_description_contains_counts():
    description = _build_description(
        make_asset(), {"typosquat": 2, "ct": 1}, indicator_count=3, exposed_count=4
    )
    assert "3 indicateur(s)" in description
    assert "2 domaine(s) de typosquatting" in description
    assert "4 IP(s) exposée(s)" in description


def _session_with_existing(existing: Threat | None = None) -> MagicMock:
    session = MagicMock()
    query = MagicMock()
    query.filter_by.return_value.first.return_value = existing
    session.query.return_value = query
    return session


def test_upsert_creates_campaign_for_institution():
    session = _session_with_existing()
    asset = make_asset()
    indicators = [make_indicator("typosquat:minfi")]

    threat = _upsert_threat(
        session, asset, Counter({"typosquat": 1}), indicators, []
    )

    session.add.assert_called_once_with(threat)
    assert threat.target_institution_id == asset.id
    assert threat.threat_type == ThreatType.campaign
    assert threat.tlp == TLPLevel.CLEAR
    assert threat.indicators == indicators


def test_upsert_replaces_existing_cluster_content():
    asset = make_asset()
    existing = Threat()
    existing.id = uuid4()
    existing.target_institution_id = asset.id
    existing.threat_type = ThreatType.campaign
    existing.tlp = TLPLevel.CLEAR
    existing.indicators = [make_indicator("ct:minfi")]
    session = _session_with_existing(existing)
    replacement = [make_indicator("nrd_watch:minfi")]

    threat = _upsert_threat(
        session, asset, Counter({"nrd_watch": 1}), replacement, ["192.0.2.1"]
    )

    session.add.assert_not_called()
    assert threat is existing
    assert threat.indicators == replacement
    assert "surface d'attaque" in threat.name


def test_get_threats_for_unknown_indicator_returns_empty():
    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = None
    assert get_threats_for_indicator(session, str(uuid4())) == []


def test_get_threats_for_indicator_serializes_associations():
    indicator = make_indicator("typosquat:minfi")
    threat = Threat()
    threat.id = uuid4()
    threat.name = "Campagne MINFI"
    threat.threat_type = ThreatType.campaign
    threat.description = "Description"
    threat.indicators = [indicator]
    indicator.threats = [threat]
    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = indicator

    result = get_threats_for_indicator(session, str(indicator.id))

    assert result == [{
        "threat_id": str(threat.id),
        "name": "Campagne MINFI",
        "threat_type": "campaign",
        "description": "Description",
        "indicator_count": 1,
    }]
