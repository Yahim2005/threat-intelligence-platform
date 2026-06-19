"""Tests du filtre anti-faux-positifs — core/quality.py.
Aucun accès réseau : utilise data/tranco_top10k.csv et config/allowlist.yaml
déjà présents sur disque.
"""
import pytest

from app.models.enums import IOCType
from core.quality import check_quality


# ── IP — cas devant être whitelistés ──────────────────────────────────────────
@pytest.mark.parametrize("value,expected_reason", [
    ("8.8.8.8", "known_public_dns"),
    ("8.8.4.4", "known_public_dns"),
    ("1.1.1.1", "known_public_dns"),
    ("10.0.0.1", "private_ip_rfc1918"),
    ("192.168.1.50", "private_ip_rfc1918"),
    ("172.16.5.5", "private_ip_rfc1918"),
    ("127.0.0.1", "loopback_ip"),
    ("169.254.1.1", "link_local_ip"),
])
def test_check_ip_false_positives(value, expected_reason):
    verdict = check_quality(value, IOCType.ip)
    assert verdict.is_false_positive is True
    assert verdict.reason == expected_reason


# ── IP — cas devant rester actifs (le cas explicite du brief J12) ────────────
def test_check_ip_malicious_stays_active():
    """Une IP publique malveillante ne doit jamais être whitelistée."""
    verdict = check_quality("185.220.101.47", IOCType.ip)
    assert verdict.is_false_positive is False
    assert verdict.reason is None


@pytest.mark.parametrize("value", [
    "45.142.214.123",
    "194.61.24.102",
    "91.219.236.18",
])
def test_check_ip_various_public_ips_stay_active(value):
    verdict = check_quality(value, IOCType.ip)
    assert verdict.is_false_positive is False


# ── IPv6 — mêmes règles que IPv4 ──────────────────────────────────────────────
def test_check_ipv6_loopback():
    verdict = check_quality("::1", IOCType.ipv6)
    assert verdict.is_false_positive is True
    assert verdict.reason == "loopback_ip"


def test_check_ipv6_public_stays_active():
    verdict = check_quality("2606:4700:4700::1111", IOCType.ipv6)  # Cloudflare DNS publique en v6
    assert verdict.is_false_positive is False


# ── Domaines — Tranco ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("domain", [
    "google.com",
    "cloudflare.com",
    "facebook.com",
])
def test_check_domain_tranco_top10k(domain):
    verdict = check_quality(domain, IOCType.domain)
    assert verdict.is_false_positive is True
    assert verdict.reason == "tranco_top10k"


def test_check_domain_not_in_tranco_stays_active():
    verdict = check_quality("evil-c2-totally-fake-12345.com", IOCType.domain)
    assert verdict.is_false_positive is False
    assert verdict.reason is None


def test_check_domain_case_insensitive():
    """La casse ne doit pas influencer la détection (GOOGLE.COM == google.com)."""
    verdict = check_quality("GOOGLE.COM", IOCType.domain)
    assert verdict.is_false_positive is True


# ── Types non couverts par les règles actuelles ───────────────────────────────
@pytest.mark.parametrize("value,ioc_type", [
    ("d41d8cd98f00b204e9800998ecf8427e", IOCType.md5),
    ("http://evil.com/payload", IOCType.url),
    ("CVE-2024-1234", IOCType.cve),
])
def test_check_unsupported_types_always_active(value, ioc_type):
    """md5, url, cve... n'ont pas encore de règle de filtrage : toujours actif."""
    verdict = check_quality(value, ioc_type)
    assert verdict.is_false_positive is False