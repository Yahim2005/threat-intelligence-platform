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

# TTL : on ne ré-interroge pas AbuseIPDB si on a une entrée de moins de 7 jours
CACHE_TTL_DAYS = 7
# AbuseIPDB : on demande l'historique des 90 derniers jours
MAX_AGE_DAYS = 90
SOURCE = "abuseipdb"


def _is_cache_fresh(entry: ReputationCache) -> bool:
    """Retourne True si l'entrée de cache est encore valide (< TTL)."""
    now = datetime.now(timezone.utc)
    fetched = entry.fetched_at
    # S'assurer que fetched_at est timezone-aware
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return (now - fetched) < timedelta(days=CACHE_TTL_DAYS)


def _get_cached(session: Session, indicator_id) -> ReputationCache | None:
    """Récupère une entrée de cache existante pour cet indicateur."""
    return (
        session.query(ReputationCache)
        .filter_by(indicator_id=indicator_id, source=SOURCE)
        .first()
    )


def _upsert(
    session: Session,
    indicator_id,
    raw: dict | None,
    score: int | None,
    error: str | None,
) -> ReputationCache:
    """Crée ou met à jour l'entrée de cache pour cet indicateur."""
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
    entry.abuse_confidence_score = score
    entry.error = error
    session.commit()
    return entry


def enrich_indicator(session: Session, indicator: Indicator) -> ReputationCache | None:
    """
    Enrichit un indicateur IP avec AbuseIPDB.

    - Ne fait rien si le type n'est pas ipv4/ipv6.
    - Ne rappelle pas l'API si le cache est encore frais.
    - Stocke toujours le résultat (ou l'erreur) en base.
    """
    if indicator.type.value not in ("ip", "ipv6"):
        logger.debug("AbuseIPDB: ignoré (type=%s)", indicator.type.value)
        return None

    # Vérification du cache
    cached = _get_cached(session, indicator.id)
    if cached and _is_cache_fresh(cached):
        logger.debug(
            "AbuseIPDB: cache frais pour %s (score=%s)",
            indicator.value,
            cached.abuse_confidence_score,
        )
        return cached

    api_key = os.getenv("ABUSEIPDB_API_KEY", "")
    if not api_key:
        logger.warning("AbuseIPDB: ABUSEIPDB_API_KEY non définie, enrichissement ignoré")
        return None

    logger.info("AbuseIPDB: interrogation pour %s", indicator.value)

    try:
        response = httpx.get(
            "https://api.abuseipdb.com/api/v2/check",
            headers={"Key": api_key, "Accept": "application/json"},
            params={"ipAddress": indicator.value, "maxAgeInDays": MAX_AGE_DAYS},
            timeout=10.0,
        )

        if response.status_code == 429:
            logger.warning("AbuseIPDB: rate limit atteint pour %s", indicator.value)
            return _upsert(session, indicator.id, None, None, "rate_limit")

        if response.status_code == 401:
            logger.error("AbuseIPDB: clé API invalide")
            return _upsert(session, indicator.id, None, None, "invalid_api_key")

        response.raise_for_status()
        raw = response.json()
        score = raw.get("data", {}).get("abuseConfidenceScore")
        return _upsert(session, indicator.id, raw, score, None)

    except httpx.TimeoutException:
        logger.warning("AbuseIPDB: timeout pour %s", indicator.value)
        return _upsert(session, indicator.id, None, None, "timeout")

    except httpx.HTTPError as exc:
        logger.error("AbuseIPDB: erreur HTTP pour %s — %s", indicator.value, exc)
        return _upsert(session, indicator.id, None, None, f"http_error: {exc}")