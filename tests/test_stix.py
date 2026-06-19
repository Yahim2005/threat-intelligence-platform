"""Tests de conversion Indicator -> STIX 2.1 — core/stix.py.
Pas d'accès DB : les objets Indicator sont instanciés en mémoire seulement.
"""
from datetime import datetime
from uuid import uuid4

import pytest
from stix2.exceptions import STIXError

from app.models import Indicator, Tag
from app.models.enums import IOCType, TLPLevel
from core.stix import TLP_MARKING_IDS, to_stix


def make_indicator(value, ioc_type, tlp=TLPLevel.CLEAR, tags=None, confidence=50):
    ind = Indicator(
        id=uuid4(),
        value=value,
        type=ioc_type,
        tlp=tlp,
        confidence=confidence,
        first_seen=datetime(2026, 6, 1, 8, 0, 0),
        created_at=datetime(2026, 6, 1, 8, 0, 0),
    )
    ind.tags = tags or []
    return ind


@pytest.mark.parametrize("value,ioc_type,expected_pattern", [
    ("198.51.100.42", IOCType.ip, "[ipv4-addr:value = '198.51.100.42']"),
    ("2001:db8::1", IOCType.ipv6, "[ipv6-addr:value = '2001:db8::1']"),
    ("evil.com", IOCType.domain, "[domain-name:value = 'evil.com']"),
    ("http://evil.com/payload", IOCType.url, "[url:value = 'http://evil.com/payload']"),
    ("test@evil.com", IOCType.email, "[email-addr:value = 'test@evil.com']"),
    ("d41d8cd98f00b204e9800998ecf8427e", IOCType.md5, "[file:hashes.MD5 = 'd41d8cd98f00b204e9800998ecf8427e']"),
])
def test_to_stix_pattern_correct(value, ioc_type, expected_pattern):
    indicator = make_indicator(value, ioc_type)
    stix_obj = to_stix(indicator)
    assert stix_obj.pattern == expected_pattern


def test_to_stix_sha1_quoted_property():
    """SHA-1 nécessite une clé de propriété entre guillemets dans le pattern STIX
    (le nom de propriété contient un tiret)."""
    indicator = make_indicator("da39a3ee5e6b4b0d3255bfef95601890afd80709", IOCType.sha1)
    stix_obj = to_stix(indicator)
    assert stix_obj.pattern == "[file:hashes.'SHA-1' = 'da39a3ee5e6b4b0d3255bfef95601890afd80709']"


def test_to_stix_sha256_quoted_property():
    indicator = make_indicator(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", IOCType.sha256
    )
    stix_obj = to_stix(indicator)
    assert stix_obj.pattern == (
        "[file:hashes.'SHA-256' = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855']"
    )


def test_to_stix_asn_strips_prefix():
    indicator = make_indicator("AS12345", IOCType.asn)
    stix_obj = to_stix(indicator)
    assert stix_obj.pattern == "[autonomous-system:number = 12345]"


def test_to_stix_is_valid_stix_object():
    """L'objet retourné doit être un vrai stix2.v21.Indicator sérialisable."""
    indicator = make_indicator("198.51.100.42", IOCType.ip)
    stix_obj = to_stix(indicator)
    serialized = stix_obj.serialize()
    assert '"type": "indicator"' in serialized
    assert '"spec_version": "2.1"' in serialized
    assert stix_obj.id.startswith("indicator--")


def test_to_stix_reuses_internal_uuid():
    """L'id STIX doit être dérivé du même UUID que l'Indicator interne (idempotence)."""
    indicator = make_indicator("198.51.100.42", IOCType.ip)
    stix_obj = to_stix(indicator)
    assert stix_obj.id == f"indicator--{indicator.id}"


@pytest.mark.parametrize("tlp,expected_marking", [
    (TLPLevel.CLEAR, TLP_MARKING_IDS[TLPLevel.CLEAR]),
    (TLPLevel.GREEN, TLP_MARKING_IDS[TLPLevel.GREEN]),
    (TLPLevel.AMBER, TLP_MARKING_IDS[TLPLevel.AMBER]),
    (TLPLevel.RED, TLP_MARKING_IDS[TLPLevel.RED]),
])
def test_to_stix_tlp_marking_applied(tlp, expected_marking):
    indicator = make_indicator("198.51.100.42", IOCType.ip, tlp=tlp)
    stix_obj = to_stix(indicator)
    assert stix_obj.object_marking_refs == [expected_marking]


def test_to_stix_tags_become_labels():
    tag = Tag(id=uuid4(), name="kind:c2")
    indicator = make_indicator("198.51.100.42", IOCType.ip, tags=[tag])
    stix_obj = to_stix(indicator)
    assert "kind:c2" in stix_obj.labels
    assert "malicious-activity" in stix_obj.labels


def test_to_stix_cve_raises():
    """CVE n'est pas mappable en indicator STIX standard — doit échouer explicitement."""
    indicator = make_indicator("CVE-2024-1234", IOCType.cve)
    with pytest.raises(ValueError):
        to_stix(indicator)


def test_to_stix_confidence_propagated():
    indicator = make_indicator("198.51.100.42", IOCType.ip, confidence=75)
    stix_obj = to_stix(indicator)
    assert stix_obj.confidence == 75