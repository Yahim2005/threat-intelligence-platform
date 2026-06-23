"""
Tests pour les enrichisseurs de réputation AbuseIPDB et VirusTotal.
On mocke httpx pour ne jamais appeler les vraies APIs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.enums import IOCType, IndicatorStatus, TLPLevel
from app.models.indicator import Indicator
from app.models.reputation import ReputationCache


# ---------------------------------------------------------------------------
# Helpers : construire des objets de test sans toucher à la DB
# ---------------------------------------------------------------------------

def make_indicator(ioc_type: str = "ip", value: str = "1.2.3.4") -> Indicator:
    """Crée un Indicator en mémoire (pas persisté en DB)."""
    ind = Indicator()
    ind.id = uuid.uuid4()
    ind.value = value
    ind.type = IOCType(ioc_type)
    ind.tlp = TLPLevel.CLEAR
    ind.confidence = 50
    ind.status = IndicatorStatus.active
    ind.first_seen = datetime.now(timezone.utc)
    ind.last_seen = datetime.now(timezone.utc)
    return ind


def make_cache(
    indicator_id,
    source: str,
    age_days: int = 0,
    error: str | None = None,
    abuse_score: int | None = None,
    vt_malicious: int | None = None,
    vt_total: int | None = None,
) -> ReputationCache:
    """Crée une entrée ReputationCache en mémoire."""
    entry = ReputationCache()
    entry.id = uuid.uuid4()
    entry.indicator_id = indicator_id
    entry.source = source
    entry.fetched_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    entry.error = error
    entry.abuse_confidence_score = abuse_score
    entry.vt_malicious = vt_malicious
    entry.vt_total = vt_total
    return entry


def make_session(cached_entry=None) -> MagicMock:
    """
    Crée une session SQLAlchemy mockée.
    Si cached_entry est fourni, query().filter_by().first() le retourne.
    """
    session = MagicMock()
    query_mock = MagicMock()
    query_mock.filter_by.return_value.first.return_value = cached_entry
    session.query.return_value = query_mock
    return session


# ---------------------------------------------------------------------------
# Tests AbuseIPDB
# ---------------------------------------------------------------------------

class TestAbuseIPDB:

    def test_unsupported_type_returns_none(self):
        """AbuseIPDB ne doit rien faire pour un domaine."""
        from enrichment.abuseipdb import enrich_indicator
        session = make_session()
        indicator = make_indicator(ioc_type="domain", value="evil.com")
        result = enrich_indicator(session, indicator)
        assert result is None
        session.query.assert_not_called()

    def test_fresh_cache_skips_api(self):
        """Si le cache est frais (< 7 jours), on ne rappelle pas l'API."""
        from enrichment.abuseipdb import enrich_indicator
        indicator = make_indicator()
        cached = make_cache(indicator.id, "abuseipdb", age_days=1, abuse_score=42)
        session = make_session(cached_entry=cached)

        with patch("httpx.get") as mock_get:
            result = enrich_indicator(session, indicator)

        mock_get.assert_not_called()
        assert result is cached
        assert result.abuse_confidence_score == 42

    def test_expired_cache_calls_api(self):
        """Si le cache est expiré (> 7 jours), on appelle l'API."""
        from enrichment.abuseipdb import enrich_indicator
        indicator = make_indicator()
        # Cache expiré : 10 jours
        cached = make_cache(indicator.id, "abuseipdb", age_days=10, abuse_score=0)
        session = make_session(cached_entry=cached)

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "data": {"abuseConfidenceScore": 85, "ipAddress": "1.2.3.4"}
        }

        with patch("httpx.get", return_value=fake_response) as mock_get:
            with patch.dict("os.environ", {"ABUSEIPDB_API_KEY": "test-key"}):
                result = enrich_indicator(session, indicator)

        mock_get.assert_called_once()
        session.commit.assert_called()

    def test_no_api_key_returns_none(self):
        """Sans clé API, l'enrichissement est ignoré proprement."""
        from enrichment.abuseipdb import enrich_indicator
        indicator = make_indicator()
        session = make_session(cached_entry=None)

        with patch.dict("os.environ", {}, clear=True):
            with patch("os.getenv", return_value=""):
                result = enrich_indicator(session, indicator)

        assert result is None

    def test_rate_limit_stores_error(self):
        """Un 429 doit être stocké comme erreur, pas lever d'exception."""
        from enrichment.abuseipdb import enrich_indicator
        indicator = make_indicator()
        session = make_session(cached_entry=None)

        fake_response = MagicMock()
        fake_response.status_code = 429

        with patch("httpx.get", return_value=fake_response):
            with patch.dict("os.environ", {"ABUSEIPDB_API_KEY": "test-key"}):
                result = enrich_indicator(session, indicator)

        session.commit.assert_called()


# ---------------------------------------------------------------------------
# Tests VirusTotal
# ---------------------------------------------------------------------------

class TestVirusTotal:

    def test_unsupported_type_returns_none(self):
        """VirusTotal ne doit rien faire pour un CVE."""
        from enrichment.virustotal import enrich_indicator
        session = make_session()
        indicator = make_indicator(ioc_type="cve", value="CVE-2024-1234")
        result = enrich_indicator(session, indicator)
        assert result is None
        session.query.assert_not_called()

    def test_fresh_cache_skips_api(self):
        """Cache frais → pas d'appel API."""
        from enrichment.virustotal import enrich_indicator
        indicator = make_indicator(ioc_type="ip", value="5.6.7.8")
        cached = make_cache(
            indicator.id, "virustotal", age_days=2,
            vt_malicious=10, vt_total=72
        )
        session = make_session(cached_entry=cached)

        with patch("httpx.request") as mock_req:
            result = enrich_indicator(session, indicator)

        mock_req.assert_not_called()
        assert result.vt_malicious == 10
        assert result.vt_total == 72

    def test_ip_calls_correct_endpoint(self):
        """Une IP doit appeler /ip_addresses/{ip}."""
        from enrichment.virustotal import enrich_indicator
        indicator = make_indicator(ioc_type="ip", value="5.6.7.8")
        session = make_session(cached_entry=None)

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 5, "suspicious": 1,
                        "harmless": 60, "undetected": 6, "timeout": 0
                    }
                }
            }
        }

        with patch("httpx.request", return_value=fake_response) as mock_req:
            with patch.dict("os.environ", {"VIRUSTOTAL_API_KEY": "test-key"}):
                result = enrich_indicator(session, indicator)

        call_args = mock_req.call_args
        assert "ip_addresses/5.6.7.8" in call_args.args[1]
        session.commit.assert_called()

    def test_hash_calls_correct_endpoint(self):
        """Un hash SHA256 doit appeler /files/{hash}."""
        from enrichment.virustotal import enrich_indicator
        hash_value = "a" * 64
        indicator = make_indicator(ioc_type="sha256", value=hash_value)
        session = make_session(cached_entry=None)

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 45, "suspicious": 2,
                        "harmless": 0, "undetected": 25, "timeout": 0
                    }
                }
            }
        }

        with patch("httpx.request", return_value=fake_response) as mock_req:
            with patch.dict("os.environ", {"VIRUSTOTAL_API_KEY": "test-key"}):
                result = enrich_indicator(session, indicator)

        call_args = mock_req.call_args
        assert f"files/{hash_value}" in call_args.args[1]

    def test_not_found_stores_zero_score(self):
        """Un 404 VirusTotal doit être stocké comme score 0/0, pas une erreur."""
        from enrichment.virustotal import enrich_indicator
        indicator = make_indicator(ioc_type="ip", value="1.1.1.1")
        session = make_session(cached_entry=None)

        fake_response = MagicMock()
        fake_response.status_code = 404

        with patch("httpx.request", return_value=fake_response):
            with patch.dict("os.environ", {"VIRUSTOTAL_API_KEY": "test-key"}):
                result = enrich_indicator(session, indicator)

        session.commit.assert_called()