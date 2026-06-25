"""
Tests du moteur de clustering.
Scénario principal : un ensemble d'IOCs liés à 'emotet' forme une Threat nommée.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.enums import IOCType, IndicatorStatus, ThreatType, TLPLevel
from app.models.indicator import Indicator
from app.models.tag import Tag
from app.models.threat import Threat
from core.clustering import (
    _dominant_malware_tag,
    _dominant_source,
    _name_cluster,
    _upsert_threat,
    get_threats_for_indicator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_indicator(ioc_type: str = "ip", value: str = "1.2.3.4", source_name: str | None = None) -> Indicator:
    ind = Indicator()
    ind.id = uuid.uuid4()
    ind.value = value
    ind.type = IOCType(ioc_type)
    ind.tlp = TLPLevel.CLEAR
    ind.confidence = 50
    ind.status = IndicatorStatus.active
    ind.tags = []
    ind.threats = []
    ind.raw_metadata = {}
    ind.last_seen = datetime.now(timezone.utc)
    if source_name:
        from app.models.source import Source
        s = Source()
        s.id = uuid.uuid4()
        s.name = source_name
        ind.source = s
    else:
        ind.source = None
    return ind


def make_tag(name: str) -> Tag:
    t = Tag()
    t.id = uuid.uuid4()
    t.name = name
    return t


def make_threat(name: str, threat_type: ThreatType = ThreatType.campaign) -> Threat:
    t = Threat()
    t.id = uuid.uuid4()
    t.name = name
    t.threat_type = threat_type
    t.tlp = TLPLevel.CLEAR
    t.indicators = []
    return t


# ---------------------------------------------------------------------------
# Tests _dominant_malware_tag
# ---------------------------------------------------------------------------

class TestDominantMalwareTag:

    def test_emotet_tag_detected(self):
        """Le tag malware:emotet doit être détecté comme dominant."""
        ind1 = make_indicator()
        ind1.tags = [make_tag("malware:emotet"), make_tag("kind:trojan")]
        ind2 = make_indicator(value="2.2.2.2")
        ind2.tags = [make_tag("malware:emotet")]
        ind3 = make_indicator(value="3.3.3.3")
        ind3.tags = [make_tag("malware:trickbot")]

        result = _dominant_malware_tag([ind1, ind2, ind3])
        assert result == "emotet"

    def test_no_malware_tags_returns_none(self):
        """Sans tag malware:*, retourne None."""
        ind1 = make_indicator()
        ind1.tags = [make_tag("kind:phishing")]
        result = _dominant_malware_tag([ind1])
        assert result is None

    def test_empty_indicators(self):
        assert _dominant_malware_tag([]) is None


# ---------------------------------------------------------------------------
# Tests _dominant_source
# ---------------------------------------------------------------------------

class TestDominantSource:

    def test_openphish_is_dominant(self):
        ind1 = make_indicator(source_name="OpenPhish")
        ind2 = make_indicator(source_name="OpenPhish")
        ind3 = make_indicator(source_name="URLhaus")
        result = _dominant_source([ind1, ind2, ind3])
        assert result == "OpenPhish"

    def test_no_source_returns_none(self):
        ind1 = make_indicator()  # source=None
        result = _dominant_source([ind1])
        assert result is None


# ---------------------------------------------------------------------------
# Tests _name_cluster
# ---------------------------------------------------------------------------

class TestNameCluster:

    def test_emotet_cluster_named_malware(self):
        """Un cluster avec tag emotet dominant → nom 'Malware: Emotet'."""
        ind1 = make_indicator()
        ind1.tags = [make_tag("malware:emotet")]
        ind2 = make_indicator(value="2.2.2.2")
        ind2.tags = [make_tag("malware:emotet")]

        name, threat_type, description = _name_cluster([ind1, ind2], 1)
        assert name == "Malware: Emotet"
        assert threat_type == ThreatType.malware
        assert "emotet" in description.lower()

    def test_source_cluster_named_campaign(self):
        """Sans tag malware, le nom est basé sur la source dominante."""
        ind1 = make_indicator(source_name="OpenPhish")
        ind2 = make_indicator(source_name="OpenPhish")

        name, threat_type, description = _name_cluster([ind1, ind2], 5)
        assert "OpenPhish" in name
        assert threat_type == ThreatType.campaign

    def test_unknown_cluster_generic_name(self):
        """Sans tag ni source → nom générique."""
        ind1 = make_indicator()
        name, threat_type, description = _name_cluster([ind1], 3)
        assert "Unknown" in name or "Cluster" in name


# ---------------------------------------------------------------------------
# Tests _upsert_threat
# ---------------------------------------------------------------------------

class TestUpsertThreat:

    def _make_session(self, existing_threat=None):
        session = MagicMock()
        q = MagicMock()
        q.filter_by.return_value.first.return_value = existing_threat
        session.query.return_value = q
        return session

    def test_creates_new_threat(self):
        """Si la Threat n'existe pas, elle est créée."""
        session = self._make_session(existing_threat=None)
        ind = make_indicator()
        threat = _upsert_threat(
            session, "Malware: Emotet", ThreatType.malware,
            "Description test", [ind]
        )
        session.add.assert_called_once()
        assert threat.name == "Malware: Emotet"
        assert threat.threat_type == ThreatType.malware

    def test_updates_existing_threat(self):
        """Si la Threat existe déjà, elle est mise à jour."""
        existing = make_threat("Malware: Emotet", ThreatType.malware)
        session = self._make_session(existing_threat=existing)
        ind = make_indicator()
        threat = _upsert_threat(
            session, "Malware: Emotet", ThreatType.malware,
            "Nouvelle description", [ind]
        )
        # Pas de session.add — on met à jour l'existant
        session.add.assert_not_called()
        assert threat.description == "Nouvelle description"

    def test_indicators_added_to_threat(self):
        """Les indicateurs sont ajoutés à la Threat."""
        session = self._make_session(existing_threat=None)
        ind1 = make_indicator()
        ind2 = make_indicator(value="2.2.2.2")
        threat = _upsert_threat(
            session, "Test Threat", ThreatType.campaign,
            "desc", [ind1, ind2]
        )
        assert len(threat.indicators) == 2

    def test_no_duplicate_indicators(self):
        """Les indicateurs déjà présents ne sont pas dupliqués."""
        existing = make_threat("Malware: Emotet")
        ind = make_indicator()
        existing.indicators = [ind]  # déjà présent

        session = self._make_session(existing_threat=existing)
        threat = _upsert_threat(
            session, "Malware: Emotet", ThreatType.malware,
            "desc", [ind]  # même indicateur
        )
        assert len(threat.indicators) == 1  # pas de doublon


# ---------------------------------------------------------------------------
# Tests get_threats_for_indicator
# ---------------------------------------------------------------------------

class TestGetThreatsForIndicator:

    def test_returns_threats_for_indicator(self):
        """Retourne les Threats associées à un indicateur."""
        ind = make_indicator()
        threat = make_threat("Malware: Emotet", ThreatType.malware)
        threat.indicators = [ind]
        ind.threats = [threat]

        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = ind

        results = get_threats_for_indicator(session, str(ind.id))
        assert len(results) == 1
        assert results[0]["name"] == "Malware: Emotet"

    def test_unknown_indicator_returns_empty(self):
        """Un indicateur inexistant retourne une liste vide."""
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None

        results = get_threats_for_indicator(session, str(uuid.uuid4()))
        assert results == []