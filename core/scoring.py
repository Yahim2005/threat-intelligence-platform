"""
Moteur de scoring de confiance composite pour les indicateurs TIP — v2.

Formule (somme des poids = 1.0) :
    score = w_source        * source_reliability
          + w_corroboration * corroboration
          + w_diversity     * source_diversity
          + w_type          * type_bonus
          + w_recency       * recency
          + w_malware_tag   * malware_tag_bonus
          + w_reputation    * external_reputation

v2 vs v1 — changements et raisons :
- W_REPUTATION abaissé de 0.30 à 0.05 : ReputationCache est vide à ~100% en
  pratique (enrichissement AbuseIPDB/VirusTotal jamais déclenché en masse),
  donc ce composant n'apportait aucune variance, juste une constante 0.5
  qui aplatissait le score. Poids résiduel conservé pour le jour où
  l'enrichissement sera branché en routine.
- Ajout de source_diversity : compte les SOURCES DISTINCTES (pas juste le
  nombre total de sightings) — un IOC confirmé par 3 sources indépendantes
  est un signal bien plus fort qu'un IOC vu 5 fois par la même source.
- Ajout de type_bonus : fiabilité intrinsèque par type d'IOC. Un hash
  cryptographique ne ment pas ; une URL est volatile par nature.
- Ajout de malware_tag_bonus : présence d'un tag malware:* nommé = signal
  de qualité (le pipeline a pu identifier une famille connue).
- Composant "contexte enrichi" (GeoIP/DNS/WHOIS) volontairement EXCLU de
  cette version : ces enrichisseurs existent mais ne sont pas encore
  appelés en routine (0 donnée réelle disponible). Ajouter ce composant
  maintenant referait la même erreur que l'ancien W_REPUTATION = 0.30.

Chaque composante est normalisée sur [0.0, 1.0]. Le score final est sur
[0, 100] (entier). Les poids sont documentés et modifiables ici.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.indicator import Indicator
from app.models.reputation import ReputationCache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Poids des composantes (somme = 1.0)
# ---------------------------------------------------------------------------
W_SOURCE        = 0.22  # Fiabilité de la source (note Admiralty)
W_CORROBORATION = 0.18  # Nombre total de sightings
W_DIVERSITY     = 0.17  # Nombre de SOURCES DISTINCTES (corroboration indépendante)
W_TYPE          = 0.16  # Fiabilité intrinsèque du type d'IOC
W_RECENCY       = 0.14  # Récence de la dernière observation
W_MALWARE_TAG   = 0.08  # Présence d'un tag malware:* nommé
W_REPUTATION    = 0.05  # Signaux externes (AbuseIPDB, VirusTotal) — résiduel, voir docstring

# Decay de récence : au-delà de DECAY_DAYS, score minimal RECENCY_FLOOR
DECAY_DAYS = 90
RECENCY_FLOOR = 0.1

# ---------------------------------------------------------------------------
# Notes Admiralty par source (A=1.0, B=0.8, C=0.6, D=0.4, E=0.2, F=0.5)
# ---------------------------------------------------------------------------
SOURCE_RELIABILITY: dict[str, float] = {
    "cisa":             1.0,
    "cisa_kev":         1.0,
    "abuseipdb":        0.8,
    "spamhaus":         0.8,
    "feodo":            0.8,
    "feodotracker":     0.8,
    "urlhaus":          0.75,
    "threatfox":        0.75,
    "openphish":        0.75,
    "malwarebazaar":    0.75,
    "tor_exit_nodes":   0.70,
    "tor":              0.70,
    "otx":              0.65,
    "alienvault":       0.65,
    "alienvault_otx":   0.65,
    "nvd":              0.80,
}
_DEFAULT_RELIABILITY = 0.5  # Note F — fiabilité inconnue

# ---------------------------------------------------------------------------
# Fiabilité intrinsèque par type d'IOC (composant "type_bonus")
# ---------------------------------------------------------------------------
TYPE_RELIABILITY: dict[str, float] = {
    "cve":    0.90,  # Vulnérabilité confirmée, source NVD/CISA, peu de faux positifs
    "sha256": 0.80,  # Hash cryptographique fort, collisions quasi impossibles
    "sha1":   0.75,
    "md5":    0.65,  # Collisions possibles mais reste un identifiant fiable
    "asn":    0.60,
    "ip":     0.55,  # Peut changer de propriétaire/usage
    "cidr":   0.55,
    "ipv6":   0.55,
    "domain": 0.50,  # Peut être repris légitimement après expiration
    "email":  0.50,
    "url":    0.45,  # Très volatile, durée de vie courte
}
_DEFAULT_TYPE_RELIABILITY = 0.5


# ---------------------------------------------------------------------------
# Composante 1 : Fiabilité de la source
# ---------------------------------------------------------------------------

def _compute_source_reliability(indicator: Indicator) -> float:
    """Retourne le poids Admiralty de la source de l'indicateur."""
    if not indicator.source:
        return _DEFAULT_RELIABILITY
    source_name = indicator.source.name.lower().strip()
    for key, weight in SOURCE_RELIABILITY.items():
        if key in source_name or source_name in key:
            return weight
    return _DEFAULT_RELIABILITY


# ---------------------------------------------------------------------------
# Composante 2 : Corroboration (nombre total de sightings)
# ---------------------------------------------------------------------------

def _compute_corroboration(indicator: Indicator, session: Session) -> float:
    """
    Score basé sur le nombre total de sightings (observations, toutes
    sources confondues). Courbe : 1→0.2, 2→0.5, 3→0.7, 5+→1.0
    """
    from app.models.sighting import Sighting
    count = (
        session.query(Sighting)
        .filter_by(indicator_id=indicator.id)
        .count()
    )
    if count >= 5:
        return 1.0
    elif count >= 3:
        return 0.7
    elif count >= 2:
        return 0.5
    elif count >= 1:
        return 0.2
    else:
        return 0.1


# ---------------------------------------------------------------------------
# Composante 3 : Diversité des sources (NOUVEAU en v2)
# ---------------------------------------------------------------------------

def _compute_source_diversity(indicator: Indicator, session: Session) -> float:
    """
    Score basé sur le nombre de SOURCES DISTINCTES ayant observé l'IOC
    (via Sighting.source_ref). Capture la corroboration indépendante :
    un IOC confirmé par 3 flux différents est un signal bien plus fort
    qu'un IOC vu 5 fois par le même flux.
    Courbe : 1 source→0.2, 2→0.55, 3→0.8, 4+→1.0
    """
    from app.models.sighting import Sighting
    distinct_sources = (
        session.query(Sighting.source_ref)
        .filter_by(indicator_id=indicator.id)
        .filter(Sighting.source_ref.isnot(None))
        .distinct()
        .count()
    )
    if distinct_sources >= 4:
        return 1.0
    elif distinct_sources >= 3:
        return 0.8
    elif distinct_sources >= 2:
        return 0.55
    elif distinct_sources >= 1:
        return 0.2
    else:
        return 0.1


# ---------------------------------------------------------------------------
# Composante 4 : Type d'IOC (NOUVEAU en v2)
# ---------------------------------------------------------------------------

def _compute_type_bonus(indicator: Indicator) -> float:
    """Fiabilité intrinsèque selon le type d'IOC (voir TYPE_RELIABILITY)."""
    if not indicator.type:
        return _DEFAULT_TYPE_RELIABILITY
    type_str = indicator.type.value if hasattr(indicator.type, "value") else str(indicator.type)
    return TYPE_RELIABILITY.get(type_str.lower(), _DEFAULT_TYPE_RELIABILITY)


# ---------------------------------------------------------------------------
# Composante 5 : Récence
# ---------------------------------------------------------------------------

def _compute_recency(indicator: Indicator) -> float:
    """Décroissance linéaire basée sur last_seen. 1.0 aujourd'hui → RECENCY_FLOOR à DECAY_DAYS jours."""
    last_seen = indicator.last_seen
    if last_seen is None:
        return RECENCY_FLOOR

    now = datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    age_days = (now - last_seen).days
    if age_days <= 0:
        return 1.0
    if age_days >= DECAY_DAYS:
        return RECENCY_FLOOR

    decay = 1.0 - (age_days / DECAY_DAYS) * (1.0 - RECENCY_FLOOR)
    return round(decay, 4)


# ---------------------------------------------------------------------------
# Composante 6 : Tag malware nommé (NOUVEAU en v2)
# ---------------------------------------------------------------------------

def _compute_malware_tag_bonus(indicator: Indicator) -> float:
    """
    1.0 si l'IOC porte au moins un tag malware:* (famille identifiée par
    le pipeline), 0.3 sinon (IOC générique, non contextualisé).
    """
    if not indicator.tags:
        return 0.3
    for tag in indicator.tags:
        if tag.name.startswith("malware:"):
            return 1.0
    return 0.3


# ---------------------------------------------------------------------------
# Composante 7 : Réputation externe (poids résiduel en v2)
# ---------------------------------------------------------------------------

def _compute_external_reputation(indicator: Indicator, session: Session) -> float:
    """
    Agrège les signaux AbuseIPDB et VirusTotal depuis reputation_cache.
    Retourne 0.5 (neutre) si aucune donnée — poids volontairement faible
    en v2 (W_REPUTATION=0.05) car ce cas est actuellement la quasi-totalité
    des IOCs.
    """
    caches = (
        session.query(ReputationCache)
        .filter_by(indicator_id=indicator.id)
        .filter(ReputationCache.error.is_(None))
        .all()
    )

    scores = []
    for cache in caches:
        if cache.source == "abuseipdb" and cache.abuse_confidence_score is not None:
            scores.append(cache.abuse_confidence_score / 100.0)
        elif cache.source == "virustotal":
            if cache.vt_total and cache.vt_total > 0:
                scores.append(cache.vt_malicious / cache.vt_total)
            elif cache.vt_total == 0:
                scores.append(0.1)

    if not scores:
        return 0.5

    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Formule composite
# ---------------------------------------------------------------------------

def compute_confidence(indicator: Indicator, session: Session) -> dict:
    """
    Calcule le score de confiance composite d'un indicateur (v2, 7 composants).

    Retourne un dict avec :
    - 'score'      : int [0, 100] — le score final
    - 'components' : dict — les 7 composantes individuelles (explicabilité)
    - 'weights'    : dict — les poids appliqués

    Le score ET les composantes sont stockés dans indicator.raw_metadata
    sous la clé 'score_components' pour l'explicabilité dans le dashboard.
    """
    source_rel    = _compute_source_reliability(indicator)
    corroboration = _compute_corroboration(indicator, session)
    diversity     = _compute_source_diversity(indicator, session)
    type_bonus    = _compute_type_bonus(indicator)
    recency       = _compute_recency(indicator)
    malware_tag   = _compute_malware_tag_bonus(indicator)
    reputation    = _compute_external_reputation(indicator, session)

    raw_score = (
        W_SOURCE        * source_rel
        + W_CORROBORATION * corroboration
        + W_DIVERSITY     * diversity
        + W_TYPE          * type_bonus
        + W_RECENCY       * recency
        + W_MALWARE_TAG   * malware_tag
        + W_REPUTATION    * reputation
    )

    score = max(0, min(100, round(raw_score * 100)))

    components = {
        "source_reliability": round(source_rel, 4),
        "corroboration":      round(corroboration, 4),
        "source_diversity":   round(diversity, 4),
        "type_bonus":         round(type_bonus, 4),
        "recency":            round(recency, 4),
        "malware_tag_bonus":  round(malware_tag, 4),
        "external_reputation": round(reputation, 4),
    }

    result = {
        "score":      score,
        "components": components,
        "weights": {
            "source":        W_SOURCE,
            "corroboration": W_CORROBORATION,
            "diversity":     W_DIVERSITY,
            "type":          W_TYPE,
            "recency":       W_RECENCY,
            "malware_tag":   W_MALWARE_TAG,
            "reputation":    W_REPUTATION,
        },
    }

    metadata = indicator.raw_metadata or {}
    metadata["score_components"] = components
    indicator.raw_metadata = metadata
    indicator.confidence = score

    logger.debug(
        "Score %s : %d (src=%.2f, corr=%.2f, div=%.2f, type=%.2f, rec=%.2f, tag=%.2f, rep=%.2f)",
        indicator.value, score,
        source_rel, corroboration, diversity, type_bonus, recency, malware_tag, reputation,
    )

    return result
