"""Tests de parsing J8 — CISA KEV, Tor Exit, NVD.
Aucun accès réseau : fixtures locales uniquement.
"""
from datetime import datetime

from app.models.enums import IOCType
from collectors.cisa_kev import CisaKevCollector
from collectors.tor_exit import TorExitCollector
from collectors.nvd import NvdCollector


# ── CISA KEV ─────────────────────────────────────────────────────────────────
KEV_FIXTURE = {
    "vulnerabilities": [
        {
            "cveID": "CVE-2026-54420",
            "vendorProject": "LiteSpeed",
            "product": "cPanel Plugin",
            "vulnerabilityName": "LiteSpeed Symlink Vulnerability",
            "dateAdded": "2026-06-15",
            "dueDate": "2026-06-18",
            "knownRansomwareCampaignUse": "Unknown",
        },
    ]
}


def test_kev_parse_count():
    records = CisaKevCollector().parse(KEV_FIXTURE)
    assert len(records) == 1


def test_kev_parse_fields():
    record = CisaKevCollector().parse(KEV_FIXTURE)[0]
    assert record["type"] == IOCType.cve
    assert record["value"] == "CVE-2026-54420"
    assert record["tag_names"] == ["kev", "cve"]
    assert record["metadata"]["vendor"] == "LiteSpeed"
    assert isinstance(record["seen_at"], datetime)


# ── Tor Exit ─────────────────────────────────────────────────────────────────
TOR_EXIT_FIXTURE = """171.25.193.25
80.67.167.81

198.98.51.189
"""


def test_tor_exit_parse_count():
    records = TorExitCollector().parse(TOR_EXIT_FIXTURE)
    assert len(records) == 3  # ligne vide ignorée


def test_tor_exit_parse_fields():
    record = TorExitCollector().parse(TOR_EXIT_FIXTURE)[0]
    assert record["type"] == IOCType.ip
    assert record["value"] == "171.25.193.25"
    assert record["tag_names"] == ["tor-exit"]


# ── NVD ──────────────────────────────────────────────────────────────────────
NVD_FIXTURE = [
    {
        "cve": {
            "id": "CVE-1999-0095",
            "lastModified": "2026-04-16T00:27:16.627",
            "vulnStatus": "Modified",
            "descriptions": [
                {"lang": "en", "value": "The debug command in Sendmail is enabled."},
                {"lang": "es", "value": "El comando de depuracion."},
            ],
            "metrics": {
                "cvssMetricV2": [
                    {
                        "cvssData": {"baseScore": 10.0},
                        "baseSeverity": "HIGH",
                    }
                ]
            },
        }
    }
]


def test_nvd_parse_count():
    records = NvdCollector().parse(NVD_FIXTURE)
    assert len(records) == 1


def test_nvd_parse_fields():
    record = NvdCollector().parse(NVD_FIXTURE)[0]
    assert record["type"] == IOCType.cve
    assert record["value"] == "CVE-1999-0095"
    assert record["tag_names"] == ["cve"]
    assert record["metadata"]["cvss_score"] == 10.0
    assert record["metadata"]["cvss_severity"] == "HIGH"
    assert record["metadata"]["description"] == "The debug command in Sendmail is enabled."