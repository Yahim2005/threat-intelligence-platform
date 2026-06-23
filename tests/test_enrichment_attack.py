from enrichment.attack import map_indicator, _heuristic_tags, _heuristic_source, _load_index
from app.models.enums import IOCType, IndicatorStatus, TLPLevel
from app.models.indicator import Indicator
from app.models.tag import Tag
from unittest.mock import MagicMock
import uuid
from datetime import datetime, timezone

def make_indicator(ioc_type="url", value="http://evil.com"):
    ind = Indicator()
    ind.id = uuid.uuid4()
    ind.value = value
    ind.type = IOCType(ioc_type)
    ind.tlp = TLPLevel.CLEAR
    ind.confidence = 50
    ind.status = IndicatorStatus.active
    ind.tags = []
    ind.source = None
    return ind

def make_tag(name):
    t = Tag()
    t.name = name
    return t

def make_session():
    session = MagicMock()
    session.query.return_value.filter_by.return_value.delete.return_value = None
    return session

# Test 1 : IOC phishing → T1566
def test_phishing_tag_maps_to_T1566():
    index = _load_index()
    ind = make_indicator(ioc_type="url", value="http://phish.com")
    # Ajoute un tag kind:phishing (adapte selon l'attribut réel)
    tag = make_tag("kind:phishing")
    ind.tags = [tag]
    results = _heuristic_tags(ind, index)
    technique_ids = [r[0] for r in results]
    assert "T1566" in technique_ids

# Test 2 : source OpenPhish → T1566
def test_openphish_source_maps_to_T1566():
    index = _load_index()
    ind = make_indicator(ioc_type="url", value="http://evil.com")
    source = MagicMock()
    source.name = "OpenPhish"
    ind.source = source
    results = _heuristic_source(ind, index)
    assert any(t == "T1566" for t, _ in results)

# Test 3 : CVE → T1190
def test_cve_maps_to_T1190():
    from enrichment.attack import _heuristic_ioc_type
    index = _load_index()
    ind = make_indicator(ioc_type="cve", value="CVE-2024-1234")
    results = _heuristic_ioc_type(ind, index)
    assert any(t == "T1190" for t, _ in results)

# Test 4 : indicateur sans contexte → aucun mapping
def test_no_context_no_mapping():
    index = _load_index()
    ind = make_indicator(ioc_type="ip", value="1.2.3.4")
    from enrichment.attack import _heuristic_tags, _heuristic_source, _heuristic_ioc_type
    results = (
        _heuristic_tags(ind, index) +
        _heuristic_source(ind, index) +
        _heuristic_ioc_type(ind, index)
    )
    assert results == []