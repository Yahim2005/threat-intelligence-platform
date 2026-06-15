"""Tests de parsing J6 — Feodo, ThreatFox, Spamhaus.
Aucun accès réseau : les fixtures simulent les réponses réelles.
"""
from datetime import datetime

import pytest

from app.models.enums import IOCType
from collectors.feodo import FeodoCollector
from collectors.spamhaus import SpamhausDropCollector
from collectors.threatfox import ThreatFoxCollector


# ── Feodo ────────────────────────────────────────────────────────────────────

FEODO_FIXTURE = [
    {
        "ip_address": "185.220.101.47",
        "port": 443,
        "status": "online",
        "country": "DE",
        "as_name": "RETN-AS",
        "first_seen": "2026-06-15 08:00:00 UTC",
        "malware": "Dridex",
    },
    {
        "ip_address": "",          # entrée vide → ignorée
        "port": 80,
        "status": "offline",
        "country": "US",
        "as_name": "SOME-AS",
        "first_seen": "date_invalide",   # date invalide → utcnow()
        "malware": "",
    },
]


def test_feodo_parse_count():
    records = FeodoCollector().parse(FEODO_FIXTURE)
    assert len(records) == 1          # l'entrée vide est ignorée


def test_feodo_parse_fields():
    record = FeodoCollector().parse(FEODO_FIXTURE)[0]
    assert record["value"] == "185.220.101.47"
    assert record["type"] == IOCType.ip
    assert record["tags"]["malware"] == "Dridex"
    assert record["context"]["port"] == 443
    assert record["context"]["country"] == "DE"
    assert isinstance(record["seen_at"], datetime)


# ── ThreatFox ─────────────────────────────────────────────────────────────────

THREATFOX_FIXTURE = {
    "query_status": "ok",
    "data": [
        {
            "id": "1",
            "ioc": "192.168.1.1:8080",
            "ioc_type": "ip:port",
            "malware_printable": "Emotet",
            "threat_type": "botnet_cc",
            "confidence_level": 90,
            "first_seen": "2026-06-15 08:00:00 UTC",
            "reporter": "analyst_x",
            "reference": None,
        },
        {
            "id": "2",
            "ioc": "evil.example.com",
            "ioc_type": "domain",
            "malware_printable": "Dridex",
            "threat_type": "botnet_cc",
            "confidence_level": 75,
            "first_seen": "2026-06-15 09:00:00 UTC",
            "reporter": "analyst_y",
            "reference": "https://example.com/report",
        },
        {
            "id": "3",
            "ioc": "CVE-2024-1234",
            "ioc_type": "cve",        # type non supporté → ignoré
            "malware_printable": "",
            "threat_type": "exploit",
            "confidence_level": 50,
            "first_seen": "2026-06-15 09:00:00 UTC",
            "reporter": "analyst_z",
            "reference": None,
        },
    ],
}


def test_threatfox_parse_skips_unsupported_type():
    records = ThreatFoxCollector().parse(THREATFOX_FIXTURE)
    assert len(records) == 2          # "cve" ignoré


def test_threatfox_parse_ip_port_split():
    record = ThreatFoxCollector().parse(THREATFOX_FIXTURE)[0]
    assert record["value"] == "192.168.1.1"   # IP extraite sans le port
    assert record["type"] == IOCType.ip
    assert record["context"]["port"] == "8080"


def test_threatfox_parse_domain():
    record = ThreatFoxCollector().parse(THREATFOX_FIXTURE)[1]
    assert record["value"] == "evil.example.com"
    assert record["type"] == IOCType.domain


# ── Spamhaus ──────────────────────────────────────────────────────────────────

SPAMHAUS_FIXTURE = """; Spamhaus DROP List 2026/06/15
; Last-Modified: Sun, 15 Jun 2026 00:00:00 UTC
1.10.16.0/20 ; SBL256704
5.8.37.0/24  ; SBL264013
"""


def test_spamhaus_parse_count():
    records = SpamhausDropCollector().parse(SPAMHAUS_FIXTURE)
    assert len(records) == 2          # les 2 lignes commentaires ignorées


def test_spamhaus_parse_fields():
    record = SpamhausDropCollector().parse(SPAMHAUS_FIXTURE)[0]
    assert record["value"] == "1.10.16.0/20"
    assert record["type"] == IOCType.cidr
    assert record["context"]["sbl_reference"] == "SBL256704"