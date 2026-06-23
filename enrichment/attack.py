from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.attack_mapping import AttackMapping
from app.models.indicator import Indicator

logger = logging.getLogger(__name__)

# Chargement de l'index ATT&CK au démarrage du module (une seule fois)
_INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "attack" / "techniques.json"
_index: dict | None = None


def _load_index() -> dict:
    """Charge l'index techniques.json en mémoire (lazy, une seule fois)."""
    global _index
    if _index is None:
        with open(_INDEX_PATH, encoding="utf-8") as f:
            _index = json.load(f)
        logger.info(
            "Index ATT&CK chargé : %d techniques, %d malwares",
            len(_index["techniques"]),
            len(_index["malware_techniques"]),
        )
    return _index


def _get_technique(index: dict, technique_id: str) -> dict | None:
    """Retrouve une technique par son ID (ex: T1566)."""
    for t in index["techniques"]:
        if t["technique_id"] == technique_id:
            return t
    return None


def _make_mapping(
    indicator_id,
    technique_id: str,
    tactic: str | None,
    confidence: int,
) -> AttackMapping:
    """Construit un objet AttackMapping (non persisté)."""
    m = AttackMapping()
    m.id = uuid4()
    m.indicator_id = indicator_id
    m.technique_id = technique_id
    m.tactic = tactic
    m.confidence = confidence
    return m


def _tags_of(indicator: Indicator) -> list[str]:
    """Retourne les slugs de tags de l'indicateur, ou liste vide."""
    if not indicator.tags:
        return []
    return [t.name for t in indicator.tags]


def _source_name(indicator: Indicator) -> str:
    """Retourne le nom de la source, en minuscules."""
    if indicator.source:
        return (indicator.source.name or "").lower()
    return ""


# ---------------------------------------------------------------------------
# Heuristiques — chacune retourne une liste de (technique_id, confidence)
# ---------------------------------------------------------------------------

def _heuristic_tags(indicator: Indicator, index: dict) -> list[tuple[str, int]]:
    """
    Tags explicites → techniques.
    kind:phishing         → T1566 (confidence 85)
    kind:c2               → T1071 (confidence 80)
    kind:ransomware       → T1486 (confidence 80)
    kind:exploit          → T1190 (confidence 75)
    kind:backdoor         → T1059 (confidence 70)
    malware:<name>        → techniques du malware dans l'index (confidence 70)
    """
    results = []
    tags = _tags_of(indicator)

    TAG_MAP = {
        "kind:phishing":   ("T1566", 85),
        "kind:c2":         ("T1071", 80),
        "kind:ransomware": ("T1486", 80),
        "kind:exploit":    ("T1190", 75),
        "kind:backdoor":   ("T1059", 70),
        "kind:trojan":     ("T1059", 65),
        "kind:loader":     ("T1105", 65),
        "kind:dropper":    ("T1105", 65),
        "kind:spam":       ("T1566", 60),
        "kind:botnet":     ("T1071", 65),
        "kind:miner":      ("T1496", 75),
    }

    for tag in tags:
        if tag in TAG_MAP:
            technique_id, confidence = TAG_MAP[tag]
            results.append((technique_id, confidence))

        # Tags malware:* → lookup dans l'index
        if tag.startswith("malware:"):
            malware_name = tag.split(":", 1)[1].lower()
            techniques = index["malware_techniques"].get(malware_name, [])
            for tid in techniques[:3]:  # max 3 techniques par malware
                results.append((tid, 70))

    return results


def _heuristic_source(indicator: Indicator, index: dict) -> list[tuple[str, int]]:
    """
    Source connue → technique probable.
    openphish      → T1566 Phishing (confidence 80)
    feodo          → T1071 C2 (confidence 75)
    urlhaus        → T1566 ou T1071 selon le tag
    spamhaus       → T1566 (confidence 60)
    cisa_kev       → T1190 Exploit Public-Facing (confidence 85)
    threatfox      → dépend du tag kind:* déjà traité
    tor_exit_nodes → T1090 Proxy (confidence 75)
    """
    source = _source_name(indicator)
    SOURCE_MAP = {
        "openphish":      [("T1566", 80)],
        "feodo":          [("T1071", 75)],
        "feodotracker":   [("T1071", 75)],
        "spamhaus":       [("T1566", 60)],
        "cisa_kev":       [("T1190", 85)],
        "cisa":           [("T1190", 85)],
        "tor_exit_nodes": [("T1090", 75)],
        "tor":            [("T1090", 75)],
    }
    for key, mappings in SOURCE_MAP.items():
        if key in source:
            return mappings
    return []


def _heuristic_ioc_type(indicator: Indicator, index: dict) -> list[tuple[str, int]]:
    """
    Type d'IOC → technique générique (confidence faible, signal de base).
    cve  → T1190 Exploit Public-Facing Application (confidence 70)
    url  → T1566.002 Spearphishing Link (confidence 40) — très générique
    """
    ioc_type = indicator.type.value
    results = []

    if ioc_type == "cve":
        results.append(("T1190", 70))

    # URL avec patterns connus
    if ioc_type == "url" and indicator.value:
        url_lower = indicator.value.lower()
        if any(p in url_lower for p in ["/wp-admin/", "/wp-login/", "wp-content/plugins/"]):
            results.append(("T1190", 65))
        elif any(p in url_lower for p in [".exe", ".dll", ".ps1", ".bat", ".vbs"]):
            results.append(("T1105", 60))  # Ingress Tool Transfer

    return results


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _deduplicate(
    mappings: list[tuple[str, int]]
) -> list[tuple[str, int]]:
    """
    Si une technique apparaît plusieurs fois (via plusieurs heuristiques),
    garde la confidence la plus haute.
    """
    best: dict[str, int] = {}
    for technique_id, confidence in mappings:
        if technique_id not in best or confidence > best[technique_id]:
            best[technique_id] = confidence
    return list(best.items())


def map_indicator(session: Session, indicator: Indicator) -> list[AttackMapping]:
    """
    Mappe un indicateur aux techniques ATT&CK pertinentes.

    - Applique les heuristiques dans l'ordre (tags > source > type)
    - Déduplique (garde la confidence max par technique)
    - Supprime les mappings existants et recrée (idempotent)
    - Retourne la liste des AttackMapping persistés
    """
    index = _load_index()

    # Collecter tous les candidats (technique_id, confidence)
    candidates: list[tuple[str, int]] = []
    candidates.extend(_heuristic_tags(indicator, index))
    candidates.extend(_heuristic_source(indicator, index))
    candidates.extend(_heuristic_ioc_type(indicator, index))

    if not candidates:
        logger.debug("ATT&CK: aucun mapping pour %s (%s)", indicator.value, indicator.type.value)
        return []

    candidates = _deduplicate(candidates)

    # Supprimer les mappings existants pour cet indicateur (idempotence)
    session.query(AttackMapping).filter_by(indicator_id=indicator.id).delete()

    results = []
    for technique_id, confidence in candidates:
        technique = _get_technique(index, technique_id)
        tactic = technique["tactics"][0] if technique and technique["tactics"] else None

        mapping = _make_mapping(indicator.id, technique_id, tactic, confidence)
        session.add(mapping)
        results.append(mapping)

        logger.debug(
            "ATT&CK: %s → %s (%s) confidence=%d",
            indicator.value, technique_id,
            technique["name"] if technique else "?",
            confidence,
        )

    session.commit()
    logger.info(
        "ATT&CK: %s → %d technique(s) mappées",
        indicator.value, len(results),
    )
    return results