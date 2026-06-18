"""Tests du moteur de normalisation — détection de type et canonicalisation.
Couvre les cas normaux et les cas limites (roadmap J10 : URL avec port,
IPv6, domaine punycode, faux positifs de hash).
"""
import pytest

from app.models.enums import IOCType
from core.normalize import (
    canonicalize,
    defang,
    detect_and_normalize,
    detect_type,
    refang,
)


# ── Détection de type — cas normaux ───────────────────────────────────────────
@pytest.mark.parametrize("value,expected", [
    ("185.220.101.47", IOCType.ip),
    ("evil.com", IOCType.domain),
    ("http://evil.com/path", IOCType.url),
    ("https://evil.com/path", IOCType.url),
    ("d41d8cd98f00b204e9800998ecf8427e", IOCType.md5),
    ("da39a3ee5e6b4b0d3255bfef95601890afd80709", IOCType.sha1),
    ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", IOCType.sha256),
    ("test@evil.com", IOCType.email),
    ("CVE-2024-1234", IOCType.cve),
    ("AS12345", IOCType.asn),
    ("192.168.0.0/24", IOCType.cidr),
])
def test_detect_type_normal_cases(value, expected):
    assert detect_type(value) == expected


# ── Détection de type — cas limites ───────────────────────────────────────────
def test_detect_ipv6():
    assert detect_type("2001:db8::1") == IOCType.ipv6


def test_detect_ipv6_full_form():
    assert detect_type("2001:0db8:0000:0000:0000:0000:0000:0001") == IOCType.ipv6


def test_detect_url_with_port():
    assert detect_type("http://evil.com:8080/path") == IOCType.url


def test_detect_url_with_query_string():
    assert detect_type("https://evil.com/path?param=value&x=1") == IOCType.url


def test_detect_punycode_domain():
    assert detect_type("xn--80ak6aa92e.com") == IOCType.domain


def test_detect_unicode_domain_converts_to_punycode_valid():
    # café.com est un domaine valide une fois encodé en IDNA.
    assert detect_type("café.com") == IOCType.domain


def test_detect_cve_lowercase():
    assert detect_type("cve-2024-1234") == IOCType.cve


def test_detect_asn_lowercase():
    assert detect_type("as12345") == IOCType.asn


# ── Faux positifs à éviter (piège explicite du roadmap) ──────────────────────
def test_short_hex_number_is_not_a_hash():
    """Un nombre hexadécimal court ne doit jamais être pris pour un hash."""
    assert detect_type("123456") is None


def test_31_char_string_is_not_md5():
    """Longueur exacte requise : 31 caractères hex ne sont PAS un MD5."""
    assert detect_type("a" * 31) is None


def test_33_char_string_is_not_md5():
    """Longueur exacte requise : 33 caractères hex ne sont PAS un MD5."""
    assert detect_type("a" * 33) is None


def test_32_char_non_hex_is_not_md5():
    """Bon nombre de caractères mais charset invalide (g n'est pas hexa) : pas un MD5."""
    assert detect_type("g" * 32) is None


def test_random_word_is_not_detected():
    assert detect_type("hello") is None


def test_empty_string_returns_none():
    assert detect_type("") is None


def test_single_label_is_not_a_domain():
    """'localhost' n'a pas de TLD : ne doit pas être détecté comme domaine."""
    assert detect_type("localhost") is None


# ── Refang / Defang ────────────────────────────────────────────────────────────
def test_refang_hxxp():
    assert refang("hxxp://evil.com") == "http://evil.com"


def test_refang_hxxps():
    assert refang("hxxps://evil.com") == "https://evil.com"


def test_refang_bracketed_dot():
    assert refang("1.2.3[.]4") == "1.2.3.4"


def test_refang_bracketed_at():
    assert refang("user[@]evil.com") == "user@evil.com"


def test_defang_http():
    assert defang("http://evil.com") == "hxxp://evil[.]com"


def test_detect_type_after_refang_hxxp():
    """Le pipeline complet doit détecter correctement une valeur défangée."""
    result = detect_and_normalize("hxxp://EVIL.com/path")
    assert result == ("http://evil.com/path", IOCType.url)


def test_detect_type_after_refang_bracketed_ip():
    result = detect_and_normalize("1.2.3[.]4")
    assert result == ("1.2.3.4", IOCType.ip)
    
def test_detect_tftp_url():
    assert detect_type("tftp://85.239.151.41:69/shr") == IOCType.url


def test_detect_ftp_url():
    assert detect_type("ftp://files.evil.com/payload.exe") == IOCType.url


# ── Canonicalisation ────────────────────────────────────────────────────────────
def test_canonicalize_domain_lowercase():
    assert canonicalize("EVIL.COM", IOCType.domain) == "evil.com"


def test_canonicalize_hash_lowercase():
    assert canonicalize("D41D8CD98F00B204E9800998ECF8427E", IOCType.md5) == "d41d8cd98f00b204e9800998ecf8427e"


def test_canonicalize_url_lowercases_scheme_and_host_only():
    """Le path doit garder sa casse d'origine (sensible à la casse sur la plupart des serveurs)."""
    result = canonicalize("HTTP://EVIL.COM/MyPath", IOCType.url)
    assert result == "http://evil.com/MyPath"


def test_canonicalize_cve_uppercase():
    assert canonicalize("cve-2024-1234", IOCType.cve) == "CVE-2024-1234"


def test_canonicalize_ip_rejects_leading_zeros():
    """Python rejette les zéros de tête par sécurité (ambiguïté octale, CVE-2021-29921) :
    une IP malformée doit lever une exception, pas être 'réparée' silencieusement."""
    with pytest.raises(ValueError):
        canonicalize("192.168.001.001", IOCType.ip)


def test_canonicalize_cidr():
    assert canonicalize("192.168.0.5/24", IOCType.cidr) == "192.168.0.0/24"