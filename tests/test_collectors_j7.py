"""Tests de parsing J7 — OTX et OpenPhish.
Aucun accès réseau : fixtures locales uniquement.
"""
from datetime import datetime

from app.models.enums import IOCType
from collectors.openphish import OpenPhishCollector
from collectors.otx import OTXCollector


# ── OTX ──────────────────────────────────────────────────────────────────────

OTX_FIXTURE = [
    {
        "id": "pulse_abc123",
        "name": "Dridex C2 Campaign June 2026",
        "indicators": [
            {
                "type": "IPv4",
                "indicator": "185.220.101.47",
                "created": "2026-06-15T08:00:00",
                "description": "C2 server",
            },
            {
                "type": "domain",
                "indicator": "evil-dridex.com",
                "created": "2026-06-15T08:00:00",
                "description": "",
            },
            {
                "type": "FileHash-MD5",
                "indicator": "d41d8cd98f00b204e9800998ecf8427e",
                "created": "2026-06-15T08:00:00",
                "description": "dropper",
            },
            {
                "type": "CVE",              # type non supporté → ignoré
                "indicator": "CVE-2024-1234",
                "created": "2026-06-15T08:00:00",
                "description": "",
            },
        ],
    },
    {
        "id": "pulse_def456",
        "name": "Phishing Kit 2026",
        "indicators": [
            {
                "type": "URL",
                "indicator": "http://phish.example.com/login",
                "created": "2026-06-15T09:00:00",
                "description": "",
            },
        ],
    },
]


def test_otx_parse_count():
    records = OTXCollector().parse(OTX_FIXTURE)
    assert len(records) == 4          # CVE ignorée → 3 + 1 = 4


def test_otx_parse_ip():
    records = OTXCollector().parse(OTX_FIXTURE)
    ip_record = next(r for r in records if r["type"] == IOCType.ip)
    assert ip_record["value"] == "185.220.101.47"
    assert ip_record["metadata"]["pulse_name"] == "Dridex C2 Campaign June 2026"
    assert ip_record["context"]["pulse_id"] == "pulse_abc123"


def test_otx_parse_pulse_name_preserved():
    """Le nom du pulse est conservé sur chaque indicateur — clé de corrélation future."""
    records = OTXCollector().parse(OTX_FIXTURE)
    phishing = next(r for r in records if r["type"] == IOCType.url)
    assert phishing["metadata"]["pulse_name"] == "Phishing Kit 2026"


def test_otx_parse_skips_unsupported_type():
    records = OTXCollector().parse(OTX_FIXTURE)
    types = [r["type"] for r in records]
    assert IOCType.ip in types
    assert IOCType.domain in types
    assert IOCType.md5 in types
    assert IOCType.url in types
    # Vérifier qu'aucun record ne vient de la CVE
    assert all(r["value"] != "CVE-2024-1234" for r in records)


# ── OpenPhish ─────────────────────────────────────────────────────────────────

OPENPHISH_FIXTURE = """https://evil-phish.com/secure/login
https://bank-fake.ru/auth/verify
http://phishing-site.net/paypal/update

ligne_invalide_sans_http
"""


def test_openphish_parse_count():
    records = OpenPhishCollector().parse(OPENPHISH_FIXTURE)
    assert len(records) == 3          # ligne vide et ligne invalide ignorées


def test_openphish_parse_fields():
    record = OpenPhishCollector().parse(OPENPHISH_FIXTURE)[0]
    assert record["type"] == IOCType.url
    assert record["value"] == "https://evil-phish.com/secure/login"
    assert record["metadata"]["threat_type"] == "phishing"
    assert isinstance(record["seen_at"], datetime)