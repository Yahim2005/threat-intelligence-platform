"""Tests des enrichisseurs — fixtures simulées, aucun accès réseau/DB.

On mocke les appels externes (geoip2, dns, whois) pour tester la logique
de transformation des données sans dépendance réseau.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models import Indicator
from app.models.enums import IOCType
from enrichment.geoip import GeoIPEnricher
from enrichment.dns_lookup import DNSEnricher
from enrichment.whois import WHOISEnricher
from enrichment.whois import _to_datetime


def make_indicator(value: str, ioc_type: IOCType) -> Indicator:
    return Indicator(
        id=uuid4(),
        value=value,
        type=ioc_type,
        created_at=datetime.now(timezone.utc),
    )


# ── GeoIP ─────────────────────────────────────────────────────────────────────

class TestGeoIPEnricher:
    def test_ip_returns_country_and_asn(self):
        indicator = make_indicator("185.220.101.47", IOCType.ip)

        mock_city_record = MagicMock()
        mock_city_record.country.iso_code = "DE"
        mock_city_record.country.name = "Germany"
        mock_city_record.city.name = "Frankfurt"
        mock_city_record.location.latitude = 50.1109
        mock_city_record.location.longitude = 8.6821

        mock_asn_record = MagicMock()
        mock_asn_record.autonomous_system_number = 60729
        mock_asn_record.autonomous_system_organization = "Stiftung Erneuerbare Freiheit"

        mock_city_reader = MagicMock()
        mock_city_reader.__enter__ = MagicMock(return_value=mock_city_reader)
        mock_city_reader.__exit__ = MagicMock(return_value=False)
        mock_city_reader.city.return_value = mock_city_record

        mock_asn_reader = MagicMock()
        mock_asn_reader.__enter__ = MagicMock(return_value=mock_asn_reader)
        mock_asn_reader.__exit__ = MagicMock(return_value=False)
        mock_asn_reader.asn.return_value = mock_asn_record

        with patch("enrichment.geoip.geoip2.database.Reader",
                   side_effect=[mock_city_reader, mock_asn_reader]):
            result = GeoIPEnricher().enrich(indicator)

        assert result["country_code"] == "DE"
        assert result["country_name"] == "Germany"
        assert result["asn"] == 60729
        assert result["asn_org"] == "Stiftung Erneuerbare Freiheit"

    def test_unknown_ip_returns_none_fields(self):
        import geoip2.errors
        indicator = make_indicator("192.0.2.1", IOCType.ip)

        mock_reader = MagicMock()
        mock_reader.__enter__ = MagicMock(return_value=mock_reader)
        mock_reader.__exit__ = MagicMock(return_value=False)
        mock_reader.city.side_effect = geoip2.errors.AddressNotFoundError("not found")
        mock_reader.asn.side_effect = geoip2.errors.AddressNotFoundError("not found")

        with patch("enrichment.geoip.geoip2.database.Reader", return_value=mock_reader):
            result = GeoIPEnricher().enrich(indicator)

        assert result["country_code"] is None
        assert result["country_name"] is None

    def test_ipv6_type_is_supported(self):
        """IPv6 doit être dans ioc_types."""
        assert IOCType.ipv6 in GeoIPEnricher.ioc_types

    def test_domain_type_not_supported(self):
        assert IOCType.domain not in GeoIPEnricher.ioc_types


# ── DNS ───────────────────────────────────────────────────────────────────────

class TestDNSEnricher:
    def test_ip_reverse_dns(self):
        indicator = make_indicator("185.220.101.47", IOCType.ip)

        with patch("enrichment.dns_lookup.socket.gethostbyaddr",
                   return_value=("tor-exit-47.for-privacy.net", [], ["185.220.101.47"])):
            result = DNSEnricher().enrich(indicator)

        assert result["reverse_dns"] == "tor-exit-47.for-privacy.net"

    def test_ip_reverse_dns_fails_gracefully(self):
        import socket
        indicator = make_indicator("1.2.3.4", IOCType.ip)

        with patch("enrichment.dns_lookup.socket.gethostbyaddr",
                   side_effect=socket.herror("no PTR")):
            result = DNSEnricher().enrich(indicator)

        assert result["reverse_dns"] is None

    def test_domain_a_records(self):
        indicator = make_indicator("evil.com", IOCType.domain)

        mock_answer = MagicMock()
        mock_answer.address = "1.2.3.4"

        with patch("enrichment.dns_lookup._resolver") as mock_resolver_fn:
            mock_resolver = MagicMock()
            mock_resolver_fn.return_value = mock_resolver
            mock_resolver.resolve.side_effect = lambda domain, rtype: (
                [mock_answer] if rtype == "A" else []
            )
            result = DNSEnricher().enrich(indicator)

        assert "1.2.3.4" in result["a_records"]

    def test_domain_dns_failure_returns_empty_lists(self):
        import dns.exception
        indicator = make_indicator("nonexistent-xyz.com", IOCType.domain)

        with patch("enrichment.dns_lookup._resolver") as mock_resolver_fn:
            mock_resolver = MagicMock()
            mock_resolver_fn.return_value = mock_resolver
            mock_resolver.resolve.side_effect = dns.exception.DNSException("NXDOMAIN")
            result = DNSEnricher().enrich(indicator)

        assert result["a_records"] == []
        assert result["mx_records"] == []
        assert result["ns_records"] == []


# ── WHOIS ─────────────────────────────────────────────────────────────────────

class TestWHOISEnricher:
    def _mock_whois(self, creation_date, registrar="Test Registrar"):
        mock_w = MagicMock()
        mock_w.registrar = registrar
        mock_w.status = ["clientDeleteProhibited"]
        mock_w.creation_date = creation_date
        mock_w.expiration_date = datetime(2027, 1, 1, tzinfo=timezone.utc)
        return mock_w

    def test_old_domain_not_newly_registered(self):
        indicator = make_indicator("google.com", IOCType.domain)
        old_date = datetime(2000, 1, 1, tzinfo=timezone.utc)

        with patch("enrichment.whois.whois.whois", return_value=self._mock_whois(old_date)):
            result = WHOISEnricher().enrich(indicator)

        assert result["is_newly_registered"] is False
        assert result["domain_age_days"] > 365 * 10
        assert result["registrar"] == "Test Registrar"

    def test_new_domain_flagged_as_newly_registered(self):
        indicator = make_indicator("evil-new-domain.com", IOCType.domain)
        recent_date = datetime.now(timezone.utc).replace(
            tzinfo=timezone.utc
        ).replace(day=max(1, datetime.now().day - 5))

        with patch("enrichment.whois.whois.whois", return_value=self._mock_whois(recent_date)):
            result = WHOISEnricher().enrich(indicator)

        assert result["is_newly_registered"] is True

    def test_whois_failure_returns_empty(self):
        indicator = make_indicator("no-whois.local", IOCType.domain)

        with patch("enrichment.whois.whois.whois", side_effect=Exception("timeout")):
            result = WHOISEnricher().enrich(indicator)

        assert result == {}

    def test_to_datetime_handles_list(self):
        dt = datetime(2020, 6, 1, tzinfo=timezone.utc)
        assert _to_datetime([dt, datetime(2021, 1, 1)]) == dt

    def test_to_datetime_handles_none(self):
        assert _to_datetime(None) is None

    def test_domain_only_not_ip(self):
        assert IOCType.ip not in WHOISEnricher.ioc_types
        assert IOCType.domain in WHOISEnricher.ioc_types