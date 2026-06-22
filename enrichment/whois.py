"""Enrichisseur WHOIS : registrar, dates, âge du domaine."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import whois

from app.models import Indicator
from app.models.enums import IOCType
from enrichment.base import BaseEnricher

logger = logging.getLogger(__name__)


def _to_datetime(value) -> datetime | None:
    """Normalise les dates WHOIS (parfois list, parfois datetime, parfois str)."""
    if isinstance(value, list):
        value = value[0]
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


class WHOISEnricher(BaseEnricher):
    provider = "whois"
    ioc_types = [IOCType.domain]

    def enrich(self, indicator: Indicator) -> dict:
        result = {}
        domain = indicator.value

        try:
            w = whois.whois(domain)
        except Exception as e:
            logger.warning(f"[whois] Lookup failed for {domain!r}: {e}")
            return {}

        result["registrar"] = w.registrar
        result["status"] = w.status if isinstance(w.status, list) else [w.status] if w.status else []

        created = _to_datetime(w.creation_date)
        expires = _to_datetime(w.expiration_date)

        result["created_at"] = created.isoformat() if created else None
        result["expires_at"] = expires.isoformat() if expires else None

        if created:
            age_days = (datetime.now(timezone.utc) - created.replace(tzinfo=timezone.utc)).days
            result["domain_age_days"] = age_days
            result["is_newly_registered"] = age_days < 30
        else:
            result["domain_age_days"] = None
            result["is_newly_registered"] = None

        return result