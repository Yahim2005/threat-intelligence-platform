"""
Moteur de décroissance temporelle (decay) des indicateurs TIP.

Deux mécanismes :
1. compute_decay_factor(ioc_type, age_days) → facteur [0.0, 1.0]
   Modèle exponentiel : factor = e^(-ln(2) / half_life * age_days)

2. apply_decay(indicator, session) → nouveau statut
   Recalcule le score avec decay, bascule en `expired` sous le seuil.

Le "réveil" d'un indicateur expiré se fait via wake_up(indicator, session)
quand un nouveau sighting est enregistré.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models.indicator import Indicator
from app.models.enums import IndicatorStatus
from core.scoring import compute_confidence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chargement de la configuration
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "decay_config.yaml"
_config: dict | None = None


def _load_config() -> dict:
    global _config
    if _config is None:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _config = yaml.safe_load(f)
    return _config


def get_half_life(ioc_type: str) -> int:
    """Retourne la demi-vie en jours pour un type d'IOC donné."""
    config = _load_config()
    half_lives = config.get("half_lives", {})
    # Fallback : 30 jours si le type est inconnu
    return half_lives.get(ioc_type, 30)


def get_expiry_threshold() -> int:
    return _load_config().get("expiry_threshold", 15)


def get_warning_threshold() -> int:
    return _load_config().get("warning_threshold", 30)


# ---------------------------------------------------------------------------
# Modèle de décroissance
# ---------------------------------------------------------------------------

def compute_decay_factor(ioc_type: str, age_days: float) -> float:
    """
    Calcule le facteur de décroissance exponentielle pour un IOC.

    Formule : factor = e^(-ln(2) / half_life * age_days)

    Propriétés :
    - age_days=0          → factor=1.0  (aucune décroissance)
    - age_days=half_life  → factor=0.5  (demi-vie : pertinence réduite de moitié)
    - age_days=2*half_life → factor=0.25 (quart de pertinence)

    Le facteur est clampé à [0.01, 1.0] — jamais zéro, on garde une trace minimale.
    """
    if age_days <= 0:
        return 1.0

    half_life = get_half_life(ioc_type)
    lam = math.log(2) / half_life  # λ = ln(2) / t½
    factor = math.exp(-lam * age_days)
    return max(0.01, round(factor, 4))


def compute_age_days(indicator: Indicator) -> float:
    """Retourne l'âge de l'indicateur en jours depuis last_seen."""
    last_seen = indicator.last_seen
    if last_seen is None:
        return 999.0  # Très vieux par défaut

    now = datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    return max(0.0, (now - last_seen).total_seconds() / 86400)


# ---------------------------------------------------------------------------
# Application du decay
# ---------------------------------------------------------------------------

def apply_decay(indicator: Indicator, session: Session) -> dict:
    """
    Applique la décroissance temporelle sur un indicateur :
    1. Recalcule le score de confiance (Jour 18)
    2. Applique le facteur de décroissance selon le type et l'âge
    3. Met à jour indicator.confidence
    4. Bascule en `expired` si score < seuil, `active` sinon

    Retourne un dict avec le score avant/après et le nouveau statut.
    """
    ioc_type = indicator.type.value
    age_days = compute_age_days(indicator)
    decay_factor = compute_decay_factor(ioc_type, age_days)

    # Score de base (Jour 18)
    base_result = compute_confidence(indicator, session)
    base_score = base_result["score"]

    # Score avec decay
    decayed_score = max(0, min(100, round(base_score * decay_factor)))

    # Mise à jour du score
    indicator.confidence = decayed_score

    # Enrichir les métadonnées avec les infos de decay
    metadata = indicator.raw_metadata or {}
    metadata["decay"] = {
        "age_days":     round(age_days, 1),
        "half_life":    get_half_life(ioc_type),
        "decay_factor": decay_factor,
        "base_score":   base_score,
        "decayed_score": decayed_score,
    }
    indicator.raw_metadata = metadata

    # Transition de statut
    expiry_threshold = get_expiry_threshold()
    warning_threshold = get_warning_threshold()

    previous_status = indicator.status
    if decayed_score < expiry_threshold:
        indicator.status = IndicatorStatus.expired
    elif indicator.status == IndicatorStatus.expired:
        # Ne pas réactiver automatiquement — c'est le rôle de wake_up()
        pass
    else:
        indicator.status = IndicatorStatus.active

    status_changed = indicator.status != previous_status

    if status_changed:
        logger.info(
            "Statut changé : %s | %s → %s | score %d → %d (decay=%.3f, age=%.0fd)",
            indicator.value,
            previous_status.value,
            indicator.status.value,
            base_score,
            decayed_score,
            decay_factor,
            age_days,
        )
    else:
        logger.debug(
            "Decay : %s | score=%d (base=%d, factor=%.3f, age=%.0fd, t½=%dd)",
            indicator.value, decayed_score, base_score,
            decay_factor, age_days, get_half_life(ioc_type),
        )

    return {
        "base_score":    base_score,
        "decayed_score": decayed_score,
        "decay_factor":  decay_factor,
        "age_days":      age_days,
        "half_life":     get_half_life(ioc_type),
        "status":        indicator.status.value,
        "status_changed": status_changed,
    }


# ---------------------------------------------------------------------------
# Réveil d'un indicateur (nouveau sighting)
# ---------------------------------------------------------------------------

def wake_up(indicator: Indicator, session: Session) -> None:
    """
    "Réveille" un indicateur expiré suite à un nouveau sighting.

    - Remet le statut à `active`
    - Met à jour last_seen à maintenant
    - Recalcule le score sans decay (l'IOC vient d'être revu)
    - Commit

    À appeler depuis le collecteur quand un IOC déjà en base est revu.
    """
    now = datetime.now(timezone.utc)
    indicator.last_seen = now
    indicator.status = IndicatorStatus.active

    # Score recalculé sans decay (age_days = 0 → factor = 1.0)
    result = compute_confidence(indicator, session)
    indicator.confidence = result["score"]

    # Nettoyer les métadonnées de decay obsolètes
    metadata = indicator.raw_metadata or {}
    metadata.pop("decay", None)
    indicator.raw_metadata = metadata

    session.commit()

    logger.info(
        "Réveil : %s | statut → active | score=%d",
        indicator.value, indicator.confidence,
    )