from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.models.indicator import Indicator
from app.models.reputation import ReputationCache

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = 7
SOURCE = "virustotal"
VT_BASE = "https://www.virustotal.com/api/v3"

# Types d'IOCs supportés par cet enrichisseur
SUPPORTED_TYPES = ("ip", "ipv6", "domain", "md5", "sha1", "sha256", "url")


def _is_cache_fresh(entry: ReputationCache) -> bool:
    now = datetime.now(timezone.utc)
    fetched = entry.fetched_at
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return (now - fetched) < timedelta(days=CACHE_TTL_DAYS)


def _get_cached(session: Session, indicator_id) -> ReputationCache | None:
    return (
        session.query(ReputationCache)
        .filter_by(indicator_id=indicator_id, source=SOURCE)
        .first()
    )


def _upsert(
    session: Session,
    indicator_id,
    raw: dict | None,
    vt_malicious: int | None,
    vt_total: int | None,
    error: str | None,
) -> ReputationCache:
    entry = _get_cached(session, indicator_id)
    now = datetime.now(timezone.utc)

    if entry is None:
        entry = ReputationCache(
            id=uuid4(),
            indicator_id=indicator_id,
            source=SOURCE,
        )
        session.add(entry)

    entry.fetched_at = now
    entry.raw_response = raw
    entry.vt_malicious = vt_malicious
    entry.vt_total = vt_total
    entry.error = error
    session.commit()
    return entry


def _extract_stats(raw: dict) -> tuple[int | None, int | None]:
    """
    Extrait (malicious, total) depuis la réponse brute VirusTotal.
    Le champ 'last_analysis_stats' est commun à tous les types d'IOCs.
    """
    try:
        stats = raw["data"]["attributes"]["last_analysis_stats"]
        malicious = stats.get("malicious", 0)
        # total = somme de toutes les catégories de résultats
        total = sum(stats.values())
        return malicious, total
    except (KeyError, TypeError):
        return None, None


def _build_request(indicator: Indicator) -> tuple[str, str] | None:
    """
    Retourne (method, url) pour l'endpoint VirusTotal adapté au type d'IOC.
    Retourne None si le type n'est pas supporté.
    """
    ioc_type = indicator.type.value
    value = indicator.value

    if ioc_type in ("ip", "ipv6"):
        return "GET", f"{VT_BASE}/ip_addresses/{value}"
    elif ioc_type == "domain":
        return "GET", f"{VT_BASE}/domains/{value}"
    elif ioc_type in ("md5", "sha1", "sha256"):
        return "GET", f"{VT_BASE}/files/{value}"
    elif ioc_type == "url":
        # VirusTotal encode les URLs en base64 sans padding pour l'endpoint
        import base64
        url_id = base64.urlsafe_b64encode(value.encode()).rstrip(b"=").decode()
        return "GET", f"{VT_BASE}/urls/{url_id}"
    return None


def enrich_indicator(session: Session, indicator: Indicator) -> ReputationCache | None:
    """
    Enrichit un indicateur avec VirusTotal.

    Supporte : ipv4, ipv6, domain, md5, sha1, sha256, url.
    Respecte le cache TTL pour ne pas brûler le quota.
    """
    if indicator.type.value not in SUPPORTED_TYPES:
        logger.debug("VirusTotal: ignoré (type=%s)", indicator.type.value)
        return None

    cached = _get_cached(session, indicator.id)
    if cached and _is_cache_fresh(cached):
        logger.debug(
            "VirusTotal: cache frais pour %s (%s/%s)",
            indicator.value,
            cached.vt_malicious,
            cached.vt_total,
        )
        return cached

    api_key = os.getenv("VIRUSTOTAL_API_KEY", "")
    if not api_key:
        logger.warning("VirusTotal: VIRUSTOTAL_API_KEY non définie, enrichissement ignoré")
        return None

    request_params = _build_request(indicator)
    if request_params is None:
        return None

    method, url = request_params
    logger.info("VirusTotal: interrogation pour %s (%s)", indicator.value, indicator.type.value)

    try:
        response = httpx.request(
            method,
            url,
            headers={"x-apikey": api_key},
            timeout=15.0,
        )

        if response.status_code == 429:
            logger.warning("VirusTotal: rate limit atteint pour %s", indicator.value)
            return _upsert(session, indicator.id, None, None, None, "rate_limit")

        if response.status_code == 401:
            logger.error("VirusTotal: clé API invalide")
            return _upsert(session, indicator.id, None, None, None, "invalid_api_key")

        if response.status_code == 404:
            # IOC inconnu de VirusTotal — pas une erreur, on le note
            logger.info("VirusTotal: IOC inconnu %s", indicator.value)
            return _upsert(session, indicator.id, {"not_found": True}, 0, 0, None)

        response.raise_for_status()
        raw = response.json()
        malicious, total = _extract_stats(raw)
        return _upsert(session, indicator.id, raw, malicious, total, None)

    except httpx.TimeoutException:
        logger.warning("VirusTotal: timeout pour %s", indicator.value)
        return _upsert(session, indicator.id, None, None, None, "timeout")

    except httpx.HTTPError as exc:
        logger.error("VirusTotal: erreur HTTP pour %s — %s", indicator.value, exc)
        return _upsert(session, indicator.id, None, None, None, f"http_error: {exc}")