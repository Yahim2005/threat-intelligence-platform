"""Enrichisseur GeoIP + ASN via MaxMind GeoLite2 (bases locales, pas de réseau)."""
from __future__ import annotations

import logging
from pathlib import Path

import geoip2.database
import geoip2.errors

from app.models import Indicator
from app.models.enums import IOCType
from enrichment.base import BaseEnricher

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CITY_DB = _PROJECT_ROOT / "data" / "GeoLite2-City.mmdb"
_ASN_DB = _PROJECT_ROOT / "data" / "GeoLite2-ASN.mmdb"


class GeoIPEnricher(BaseEnricher):
    provider = "geoip"
    ioc_types = [IOCType.ip, IOCType.ipv6]

    def enrich(self, indicator: Indicator) -> dict:
        result = {}
        ip = indicator.value

        try:
            with geoip2.database.Reader(str(_CITY_DB)) as reader:
                city = reader.city(ip)
                result["country_code"] = city.country.iso_code
                result["country_name"] = city.country.name
                result["city"] = city.city.name
                result["latitude"] = city.location.latitude
                result["longitude"] = city.location.longitude
        except geoip2.errors.AddressNotFoundError:
            result["country_code"] = None
            result["country_name"] = None
        except Exception as e:
            logger.warning(f"[geoip] City lookup failed for {ip!r}: {e}")

        try:
            with geoip2.database.Reader(str(_ASN_DB)) as reader:
                asn = reader.asn(ip)
                result["asn"] = asn.autonomous_system_number
                result["asn_org"] = asn.autonomous_system_organization
        except geoip2.errors.AddressNotFoundError:
            result["asn"] = None
            result["asn_org"] = None
        except Exception as e:
            logger.warning(f"[geoip] ASN lookup failed for {ip!r}: {e}")

        return result