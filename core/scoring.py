"""
Moteur de scoring de confiance composite pour les indicateurs TIP.

Formule :
    score = w_source * source_reliability
          + w_corroboration * corroboration
          + w_reputation * external_reputation
          + w_recency * recency

Chaque composante est normalisée sur [0.0, 1.0].
Le score final est sur [0, 100] (entier).

Les poids sont documentés et modifiables ici — pas de boîte noire.
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
W_SOURCE = 0.25         # Fiabilité de la source (note Admiralty)
W_CORROBORATION = 0.25  # Nombre de sources / sightings
W_REPUTATION = 0.30     # Signaux externes (AbuseIPDB, VirusTotal)
W_RECENCY = 0.20        # Récence de la dernière observation

# Decay de récence : au-delà de DECAY_DAYS, score minimal RECENCY_FLOOR
DECAY_DAYS = 90
RECENCY_FLOOR = 0.1

# ---------------------------------------------------------------------------
# Notes Admiralty par source (A=1.0, B=0.8, C=0.6, D=0.4, E=0.2, F=0.5)
# F = fiabilité inconnue — neutre, ni bonus ni malus fort
# ---------------------------------------------------------------------------
SOURCE_RELIABILITY: dict[str, float] = {
    # A — Totalement fiable (gouvernements, CERT officiels)
    "cisa":             1.0,
    "cisa_kev":         1.0,
    # B — Généralement fiable (services réputés, données vérifiées)
    "abuseipdb":        0.8,
    "spamhaus":         0.8,
    "feodo":            0.8,
    "feodotracker":     0.8,
    "urlhaus":          0.75,
    "threatfox":        0.75,
    "openphish":        0.75,
    "tor_exit_nodes":   0.70,
    "tor":              0.70,
    # C — Assez fiable (communauté, moins de vérification)
    "otx":              0.65,
    "alienvault":       0.65,
    "alienvault_otx":   0.65,
    "nvd":              0.80,   # NVD est gouvernemental → B
    # F — Inconnu (fallback)
}
_DEFAULT_RELIABILITY = 0.5  # Note F — fiabilité inconnue


# ---------------------------------------------------------------------------
# Composante 1 : Fiabilité de la source
# ---------------------------------------------------------------------------

def _compute_source_reliability(indicator: Indicator) -> float:
    """
    Retourne le poids Admiralty de la source de l'indicateur.
    Si la source est inconnue, retourne la valeur par défaut (F = 0.5).
    """
    if not indicator.source:
        return _DEFAULT_RELIABILITY
    source_name = indicator.source.name.lower().strip()
    # Cherche une correspondance partielle dans le dictionnaire
    for key, weight in SOURCE_RELIABILITY.items():
        if key in source_name or source_name in key:
            return weight
    return _DEFAULT_RELIABILITY


# ---------------------------------------------------------------------------
# Composante 2 : Corroboration
# ---------------------------------------------------------------------------

def _compute_corroboration(indicator: Indicator, session: Session) -> float:
    """
    Score basé sur le nombre de sightings (observations indépendantes).
    Courbe : 1→0.2, 2→0.5, 3→0.7, 5+→1.0
    """
    from app.models.sighting import Sighting
    count = (
        session.query(Sighting)
        .filter_by(indicator_id=indicator.id)
        .count()
    )
    # Table de correspondance intentionnellement simple et lisible
    if count >= 5:
        return 1.0
    elif count >= 3:
        return 0.7
    elif count >= 2:
        return 0.5
    elif count >= 1:
        return 0.2
    else:
        return 0.1  # Aucun sighting enregistré


# ---------------------------------------------------------------------------
# Composante 3 : Réputation externe
# ---------------------------------------------------------------------------

def _compute_external_reputation(indicator: Indicator, session: Session) -> float:
    """
    Agrège les signaux AbuseIPDB et VirusTotal depuis reputation_cache.
    - AbuseIPDB : abuse_confidence_score / 100
    - VirusTotal : vt_malicious / vt_total
    Si les deux sont disponibles → moyenne.
    Si aucun → valeur neutre 0.5 (on ne pénalise pas l'absence de données).
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
                # Analysé, aucun moteur ne le connaît → signal faible mais pas nul
                scores.append(0.1)

    if not scores:
        return 0.5  # Neutre — pas de données de réputation

    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Composante 4 : Récence
# ---------------------------------------------------------------------------

def _compute_recency(indicator: Indicator) -> float:
    """
    Décroissance linéaire basée sur last_seen.
    1.0 aujourd'hui → RECENCY_FLOOR à DECAY_DAYS jours.
    """
    last_seen = indicator.last_seen
    if last_seen is None:
        return RECENCY_FLOOR

    now = datetime.now(timezone.utc)
    # Normaliser last_seen en timezone-aware
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    age_days = (now - last_seen).days
    if age_days <= 0:
        return 1.0
    if age_days >= DECAY_DAYS:
        return RECENCY_FLOOR

    # Interpolation linéaire entre 1.0 et RECENCY_FLOOR
    decay = 1.0 - (age_days / DECAY_DAYS) * (1.0 - RECENCY_FLOOR)
    return round(decay, 4)


# ---------------------------------------------------------------------------
# Formule composite
# ---------------------------------------------------------------------------

def compute_confidence(indicator: Indicator, session: Session) -> dict:
    """
    Calcule le score de confiance composite d'un indicateur.

    Retourne un dict avec :
    - 'score'      : int [0, 100] — le score final
    - 'components' : dict — les 4 composantes individuelles (explicabilité)
    - 'weights'    : dict — les poids appliqués

    Le score ET les composantes sont stockés dans indicator.raw_metadata
    sous la clé 'score_components' pour l'explicabilité dans le dashboard.
    """
    source_rel  = _compute_source_reliability(indicator)
    corroboration = _compute_corroboration(indicator, session)
    reputation  = _compute_external_reputation(indicator, session)
    recency     = _compute_recency(indicator)

    raw_score = (
        W_SOURCE        * source_rel
        + W_CORROBORATION * corroboration
        + W_REPUTATION    * reputation
        + W_RECENCY       * recency
    )

    # Clamp sur [0, 100] et arrondi à l'entier
    score = max(0, min(100, round(raw_score * 100)))

    components = {
        "source_reliability": round(source_rel, 4),
        "corroboration":      round(corroboration, 4),
        "external_reputation": round(reputation, 4),
        "recency":            round(recency, 4),
    }

    result = {
        "score":      score,
        "components": components,
        "weights": {
            "source":       W_SOURCE,
            "corroboration": W_CORROBORATION,
            "reputation":   W_REPUTATION,
            "recency":      W_RECENCY,
        },
    }

    # Persistance des composantes pour l'explicabilité
    metadata = indicator.raw_metadata or {}
    metadata["score_components"] = components
    indicator.raw_metadata = metadata
    indicator.confidence = score

    logger.debug(
        "Score %s : %d (src=%.2f, corr=%.2f, rep=%.2f, rec=%.2f)",
        indicator.value, score,
        source_rel, corroboration, reputation, recency,
    )

    return result