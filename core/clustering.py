"""
Moteur de clustering des indicateurs en entités Threat.

Un seul mécanisme de regroupement : l'institution camerounaise ciblée.

Les collecteurs de surveillance nationale (typosquat_monitor, ct_monitor,
nrd_monitor) posent des tags typosquat:{slug} / ct:{slug} / nrd_watch:{slug}
sur les IOCs qu'ils détectent, où {slug} est dérivé de l'institution
MonitoredAsset visée : (acronym or name[:20]).lower().replace(' ', '_')
(même convention que collectors/*.py et api/queries.py).

Peu importe lequel de ces 3 mécanismes a détecté l'IOC, tous les IOCs visant
la même institution rejoignent le même cluster. Un IOC sans aucun de ces
tags n'appartient à aucun cluster (pas de "Unknown Cluster" fourre-tout).

Les Threat sont des artefacts calculés, pas des observations primaires :
à chaque exécution, le contenu d'un cluster-institution est recalculé et
remplace intégralement l'ancien (un IOC qui n'est plus actif ou qui a perdu
son tag institution sort naturellement du cluster).
"""
from __future__ import annotations

import logging
from collections import Counter
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.enums import IndicatorStatus, ThreatType, TLPLevel
from app.models.exposed_asset import ExposedAsset
from app.models.indicator import Indicator
from app.models.monitored_asset import MonitoredAsset
from app.models.tag import Tag
from app.models.threat import Threat

logger = logging.getLogger(__name__)

# Préfixes de tag posés par les collecteurs de surveillance nationale, et
# libellés associés (utilisés pour le nom lisible et la description).
MECHANISM_LABELS = {
    "typosquat": "typosquatting",
    "ct": "certificats suspects",
    "nrd_watch": "domaines récents suspects",
}
MECHANISM_ORDER = ["typosquat", "ct", "nrd_watch"]

MECHANISM_DESC_LABELS = {
    "typosquat": "domaine(s) de typosquatting",
    "ct": "certificat(s) suspect(s) détecté(s) par CT monitoring",
    "nrd_watch": "domaine(s) nouvellement enregistré(s) suspect(s)",
}


# ---------------------------------------------------------------------------
# Résolution institution ← tag
# ---------------------------------------------------------------------------

def _slugify(asset: MonitoredAsset) -> str:
    base = asset.acronym or asset.name[:20]
    return base.lower().replace(" ", "_")


def _build_institution_index(session: Session) -> dict[str, MonitoredAsset]:
    """
    slug → MonitoredAsset, même convention de slug que les collecteurs.
    En cas de collision (deux institutions dont l'acronyme se slugifie
    pareil), la première trouvée (ordre created_at) est conservée et un
    warning est loggué -- pas de fusion silencieuse.
    """
    assets = (
        session.query(MonitoredAsset)
        .order_by(MonitoredAsset.created_at, MonitoredAsset.id)
        .all()
    )
    index: dict[str, MonitoredAsset] = {}
    for asset in assets:
        slug = _slugify(asset)
        if slug in index:
            logger.warning(
                "Collision de slug institution '%s' entre '%s' et '%s' -- "
                "'%s' est conservée pour le clustering",
                slug, index[slug].name, asset.name, index[slug].name,
            )
            continue
        index[slug] = asset
    return index


def _resolve_institution(
    indicator: Indicator,
    institution_index: dict[str, MonitoredAsset],
) -> tuple[MonitoredAsset, set[str]] | None:
    """
    Retourne (institution, mécanismes) pour un IOC, ou None s'il ne porte
    aucun tag d'institution reconnu.

    Si l'IOC porte des tags pour PLUSIEURS institutions distinctes (cas
    ambigu, censé être rare), il est assigné à la première institution
    trouvée (ordre alphabétique des tags, pour être déterministe) et un
    warning est loggué -- pas de duplication dans deux clusters.
    """
    matches: list[tuple[MonitoredAsset, str]] = []
    for tag in sorted(indicator.tags, key=lambda t: t.name):
        if ":" not in tag.name:
            continue
        prefix, slug = tag.name.split(":", 1)
        if prefix not in MECHANISM_LABELS:
            continue
        asset = institution_index.get(slug)
        if asset is not None:
            matches.append((asset, prefix))

    if not matches:
        return None

    primary = matches[0][0]
    distinct_institutions = {a.id for a, _ in matches}
    if len(distinct_institutions) > 1:
        logger.warning(
            "IOC %s porte des tags visant plusieurs institutions distinctes "
            "(%s) -- assigné à '%s' (première trouvée)",
            indicator.value,
            sorted({a.name for a, _ in matches}),
            primary.name,
        )

    mechanisms = {prefix for asset, prefix in matches if asset.id == primary.id}
    return primary, mechanisms


def mechanism_counts_for_indicators(indicators: list[Indicator]) -> Counter:
    """
    Décompte, par mécanisme (typosquat/ct/nrd_watch), le nombre d'IOCs d'une
    liste qui portent un tag de ce mécanisme. Réutilisable pour l'affichage
    (api/queries.py) sans dupliquer la logique de scan des tags.
    """
    counts: Counter = Counter()
    for ind in indicators:
        mechanisms_seen: set[str] = set()
        for tag in ind.tags:
            if ":" not in tag.name:
                continue
            prefix, _slug = tag.name.split(":", 1)
            if prefix in MECHANISM_LABELS:
                mechanisms_seen.add(prefix)
        for prefix in mechanisms_seen:
            counts[prefix] += 1
    return counts


# ---------------------------------------------------------------------------
# Nommage / description du cluster
# ---------------------------------------------------------------------------

def _build_name(asset: MonitoredAsset, mechanisms: set[str], has_exposed_assets: bool) -> str:
    parts = [MECHANISM_LABELS[m] for m in MECHANISM_ORDER if m in mechanisms]
    if has_exposed_assets:
        parts.append("surface d'attaque")
    if not parts:
        return asset.name
    return f"{asset.name} — {' + '.join(parts)}"


def _build_description(
    asset: MonitoredAsset,
    mechanism_counts: dict[str, int],
    indicator_count: int,
    exposed_count: int,
) -> str:
    mech_phrases = [
        f"{mechanism_counts[m]} {MECHANISM_DESC_LABELS[m]}"
        for m in MECHANISM_ORDER if m in mechanism_counts
    ]
    description = (
        f"{asset.name} est ciblée par {indicator_count} indicateur(s) : "
        + ", ".join(mech_phrases) + "."
    )
    if exposed_count:
        description += f" {exposed_count} IP(s) exposée(s) associée(s) à cette institution."
    return description


# ---------------------------------------------------------------------------
# Création / mise à jour d'une Threat
# ---------------------------------------------------------------------------

def _upsert_threat(
    session: Session,
    asset: MonitoredAsset,
    mechanism_counts: Counter,
    indicators: list[Indicator],
    exposed_ips: list[str],
) -> Threat:
    """
    Upsert par target_institution_id (pas par nom) : le nom peut changer
    d'une exécution à l'autre (nouveau mécanisme détecté) sans créer une
    Threat orpheline en doublon.
    """
    existing = (
        session.query(Threat)
        .filter_by(target_institution_id=asset.id)
        .first()
    )

    if existing:
        threat = existing
    else:
        threat = Threat()
        threat.id = uuid4()
        threat.target_institution_id = asset.id
        threat.threat_type = ThreatType.campaign
        threat.tlp = TLPLevel.CLEAR
        session.add(threat)
        logger.info("Nouvelle Threat créée pour l'institution : %s", asset.name)

    threat.name = _build_name(asset, set(mechanism_counts), bool(exposed_ips))
    threat.description = _build_description(
        asset, mechanism_counts, len(indicators), len(exposed_ips)
    )

    # Artefact calculé : le contenu du cluster est remplacé intégralement à
    # chaque exécution (un IOC qui sort du périmètre -- inactif, retagué --
    # doit disparaître du cluster, pas seulement en accumuler de nouveaux).
    threat.indicators = indicators

    return threat


# ---------------------------------------------------------------------------
# Orchestration principale
# ---------------------------------------------------------------------------

def extract_clusters(session: Session, dry_run: bool = False) -> list[dict]:
    """
    Regroupe les IOCs actifs par institution ciblée (tags typosquat:/ct:/
    nrd_watch:) et crée/met à jour les entités Threat correspondantes.

    Retourne une liste de dicts décrivant chaque cluster créé/mis à jour.
    """
    institution_index = _build_institution_index(session)
    if not institution_index:
        logger.warning("Aucune institution surveillée en base -- aucun cluster à extraire")
        return []

    candidate_indicators = (
        session.query(Indicator)
        .join(Indicator.tags)
        .filter(
            Indicator.status == IndicatorStatus.active,
            or_(*[Tag.name.like(f"{p}:%") for p in MECHANISM_LABELS]),
        )
        .distinct()
        .all()
    )
    logger.info(
        "%d IOCs actifs candidats (portant un tag typosquat:/ct:/nrd_watch:)",
        len(candidate_indicators),
    )

    clusters: dict[str, dict] = {}
    for indicator in candidate_indicators:
        resolved = _resolve_institution(indicator, institution_index)
        if resolved is None:
            continue
        asset, _mechanisms = resolved
        bucket = clusters.setdefault(str(asset.id), {"asset": asset, "indicators": []})
        bucket["indicators"].append(indicator)

    logger.info("%d clusters-institution identifiés", len(clusters))

    results = []
    for bucket in sorted(clusters.values(), key=lambda b: len(b["indicators"]), reverse=True):
        asset = bucket["asset"]
        indicators = bucket["indicators"]

        mechanism_counts = mechanism_counts_for_indicators(indicators)

        exposed = (
            session.query(ExposedAsset)
            .filter(ExposedAsset.monitored_asset_id == asset.id)
            .all()
        )
        exposed_ips = [e.ip_address for e in exposed]

        threat = _upsert_threat(session, asset, mechanism_counts, indicators, exposed_ips)
        session.flush()

        first_seen = min(
            (ind.first_seen for ind in indicators if ind.first_seen is not None),
            default=None,
        )

        results.append({
            "threat_id": str(threat.id),
            "name": threat.name,
            "threat_type": threat.threat_type.value,
            "institution": asset.name,
            "indicator_count": len(indicators),
            "mechanism_counts": dict(mechanism_counts),
            "exposed_ip_count": len(exposed_ips),
            "first_seen": first_seen.isoformat() if first_seen else None,
        })

    if dry_run:
        session.rollback()
        logger.info("[DRY-RUN] %d Threats auraient été créées/mises à jour", len(results))
    else:
        session.commit()
        logger.info("%d Threats créées/mises à jour", len(results))

    return results


# ---------------------------------------------------------------------------
# Endpoint interne : get_threats_for_indicator(indicator)
# ---------------------------------------------------------------------------

def get_threats_for_indicator(
    session: Session,
    indicator_id: str,
) -> list[dict]:
    """
    Retourne les Threats associées à un indicateur donné.
    Utilisé par l'API : GET /indicators/{id}/threats
    """
    indicator = session.query(Indicator).filter_by(id=indicator_id).first()
    if not indicator:
        return []

    return [
        {
            "threat_id":      str(t.id),
            "name":           t.name,
            "threat_type":    t.threat_type.value,
            "description":    t.description,
            "indicator_count": len(t.indicators),
        }
        for t in indicator.threats
    ]
