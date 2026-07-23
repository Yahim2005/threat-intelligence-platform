# api/queries.py


from __future__ import annotations
from typing import Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Indicator, Source, Tag, Threat
from app.models.monitored_asset import MonitoredAsset
from app.models.exposed_asset import ExposedAsset
from app.models.enums import DomainStatus
from app.models.enums import TLPLevel


# ─── Indicators ──────────────────────────────────────────────────────────────

def get_indicators(
    session: Session,
    ioc_type: Optional[str] = None,
    status: Optional[str] = None,
    confidence_min: Optional[int] = None,
    confidence_max: Optional[int] = None,
    source_name: Optional[str] = None,
    tag_slug: Optional[str] = None,
    tlp: Optional[str] = None,
    search: Optional[str] = None,
    cameroon: Optional[bool] = None,
    cameroon_relevance_min: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Indicator], int]:
    q = session.query(Indicator)

    if ioc_type:
        q = q.filter(Indicator.type == ioc_type)
    if status:
        q = q.filter(Indicator.status == status)
    if confidence_min is not None:
        q = q.filter(Indicator.confidence >= confidence_min)
    if confidence_max is not None:
        q = q.filter(Indicator.confidence <= confidence_max)
    if tlp:
        q = q.filter(Indicator.tlp == tlp)
    if source_name:
        q = q.join(Indicator.source).filter(Source.name == source_name)
    if tag_slug:
        q = q.join(Indicator.tags).filter(Tag.name == tag_slug)
    if cameroon:
        q = q.filter(Indicator.cameroon_relevance > 0)
    if cameroon_relevance_min is not None:
        q = q.filter(Indicator.cameroon_relevance >= cameroon_relevance_min)
    if search:
        q = q.filter(Indicator.value.ilike(f"%{search}%"))

    total = q.count()
    items = (
        q.order_by(Indicator.confidence.desc().nulls_last(), Indicator.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_indicator_by_value(session: Session, value: str) -> Optional[Indicator]:
    """
    Recherche par valeur exacte d'abord. Si rien n'est trouvé, tente une
    normalisation (utile pour les numéros de téléphone locaux comme
    '656708967' qui doivent matcher '+237656708967' en base, ou pour des
    IOCs saisis dans un format légèrement différent du format canonique).
    """
    ind = session.query(Indicator).filter(Indicator.value == value).first()
    if ind:
        return ind

    from core.normalize import detect_and_normalize
    normalized = detect_and_normalize(value)
    if normalized is None:
        return None
    norm_value, _ = normalized
    if norm_value == value:
        return None  # déjà tenté, pas la peine de refaire la même requête

    return session.query(Indicator).filter(Indicator.value == norm_value).first()


# ─── Sources ─────────────────────────────────────────────────────────────────

def get_sources(session: Session) -> list[tuple[Source, int]]:
    rows = (
        session.query(Source, func.count(Indicator.id).label("indicator_count"))
        .outerjoin(Indicator, Indicator.source_id == Source.id)
        .group_by(Source.id)
        .order_by(Source.name)
        .all()
    )
    return rows


# ─── Threats ─────────────────────────────────────────────────────────────────

def get_threats(
    session: Session,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    base = session.query(Threat)
    total = base.count()

    threats = (
        base.order_by(Threat.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    results = []
    for threat in threats:
        indicators = threat.indicators
        avg_confidence = (
            sum(i.confidence for i in indicators if i.confidence is not None) / len(indicators)
            if indicators else None
        )
        tag_counts: dict[str, int] = {}
        for ind in indicators:
            for tag in ind.tags:
                tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1
        top_tags = sorted(tag_counts, key=lambda k: tag_counts[k], reverse=True)[:5]
        cameroon_relevance = max(
            (i.cameroon_relevance for i in indicators if i.cameroon_relevance is not None),
            default=0,
        )

        results.append({
            "id": str(threat.id),
            "name": threat.name,
            "indicator_count": len(indicators),
            "avg_confidence": round(avg_confidence, 2) if avg_confidence is not None else None,
            "top_tags": top_tags,
            "cameroon_relevance": cameroon_relevance,
        })

    return results, total


# ─── Stats ───────────────────────────────────────────────────────────────────

def get_stats(session: Session) -> dict:
    total = session.query(func.count(Indicator.id)).scalar()

    status_counts = (
        session.query(Indicator.status, func.count(Indicator.id))
        .group_by(Indicator.status)
        .all()
    )
    by_status = {str(s.value if hasattr(s, "value") else s): c for s, c in status_counts}

    type_counts = (
        session.query(Indicator.type, func.count(Indicator.id))
        .group_by(Indicator.type)
        .all()
    )
    by_type = {str(t.value if hasattr(t, "value") else t): c for t, c in type_counts}

    tlp_counts = (
        session.query(Indicator.tlp, func.count(Indicator.id))
        .group_by(Indicator.tlp)
        .all()
    )
    by_tlp = {str(t.value if hasattr(t, "value") else t): c for t, c in tlp_counts if t is not None}

    avg_confidence = session.query(func.avg(Indicator.confidence)).scalar()
    total_threats = session.query(func.count(Threat.id)).scalar()
    total_sources = session.query(func.count(Source.id)).scalar()

    return {
        "total_indicators": total,
        "active_indicators": by_status.get("active", 0),
        "expired_indicators": by_status.get("expired", 0),
        "whitelisted_indicators": by_status.get("whitelisted", 0),
        "total_threats": total_threats,
        "total_sources": total_sources,
        "avg_confidence": round(float(avg_confidence), 2) if avg_confidence else None,
        "indicators_by_type": by_type,
        "indicators_by_tlp": by_tlp,
    }
    # ─── Advanced Analytics ───────────────────────────────────────────────────────

from datetime import datetime, timedelta
from sqlalchemy import cast, Date
from app.models import TIPRelationship, Sighting


def get_related_indicators(session: Session, value: str) -> list[dict]:
    """
    Trouve tous les IOCs liés à `value` via la table relationships.
    Retourne la liste avec le type de relation et la confiance.
    """
    # D'abord on récupère l'indicateur source
    ind = session.query(Indicator).filter(Indicator.value == value).first()
    if not ind:
        return []

    ind_id = str(ind.id)

    # On cherche toutes les relations où cet IOC est source OU cible
    rels = (
        session.query(TIPRelationship)
        .filter(
            (TIPRelationship.source_ref == ind_id) |
            (TIPRelationship.target_ref == ind_id)
        )
        .all()
    )

    results = []
    for rel in rels:
        # L'autre bout de la relation
        other_id = rel.target_ref if rel.source_ref == ind_id else rel.source_ref

        other = session.query(Indicator).filter(
            Indicator.id == other_id
        ).first()
        if not other:
            continue

        results.append({
            "value": other.value,
            "type": str(other.type.value if hasattr(other.type, "value") else other.type),
            "confidence": other.confidence,
            "status": str(other.status.value if hasattr(other.status, "value") else other.status),
            "relationship_type": str(rel.relationship_type.value if hasattr(rel.relationship_type, "value") else rel.relationship_type),
            "relationship_confidence": rel.confidence,
            "rule": rel.rule,
        })

    return results


def get_indicator_timeline(session: Session, value: str, days: int = 30) -> list[dict]:
    """
    Retourne le nombre de sightings par jour sur les `days` derniers jours
    pour l'indicateur identifié par `value`.
    """
    ind = session.query(Indicator).filter(Indicator.value == value).first()
    if not ind:
        return []

    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        session.query(
            cast(Sighting.seen_at, Date).label("day"),
            func.sum(Sighting.count).label("total"),
        )
        .filter(Sighting.indicator_id == ind.id)
        .filter(Sighting.seen_at >= since)
        .group_by(cast(Sighting.seen_at, Date))
        .order_by(cast(Sighting.seen_at, Date))
        .all()
    )

    return [{"date": str(row.day), "sightings": int(row.total)} for row in rows]


def get_ingestion_trends(session: Session, days: int = 30) -> list[dict]:
    """
    Retourne le nombre d'indicateurs créés par jour sur les `days` derniers jours.
    Utilisé par le dashboard pour afficher la courbe de tendance.
    """
    since = datetime.utcnow() - timedelta(days=days)

    rows = (
        session.query(
            cast(Indicator.first_seen, Date).label("day"),
            func.count(Indicator.id).label("total"),
        )
        .filter(Indicator.first_seen >= since)
        .group_by(cast(Indicator.first_seen, Date))
        .order_by(cast(Indicator.first_seen, Date))
        .all()
    )

    return [{"date": str(row.day), "count": int(row.total)} for row in rows]

def get_alerts(
    session: Session,
    threshold: int = 75,
    hours: int = 24,
    limit: int = 20,
    cameroon_only: bool = False,
) -> list[dict]:
    """
    Retourne les IOCs actifs haute confiance vus récemment.
    threshold     : score minimum (défaut 75)
    hours         : fenêtre temporelle en heures (défaut 24h)
    limit         : nombre max de résultats
    cameroon_only : ne garder que les IOCs pertinents pour le Cameroun
                    (cameroon_relevance > 0) — utilisé par le panneau
                    d'alertes Cameroun de l'Overview
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    q = (
        session.query(Indicator)
        .filter(Indicator.status == "active")
        .filter(Indicator.confidence >= threshold)
        .filter(Indicator.last_seen >= since)
    )
    if cameroon_only:
        q = q.filter(Indicator.cameroon_relevance > 0)

    rows = (
        q.order_by(Indicator.confidence.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(r.id),
            "value": r.value,
            "type": str(r.type.value if hasattr(r.type, "value") else r.type),
            "confidence": r.confidence,
            "source": r.source.name if r.source else None,
            "last_seen": r.last_seen.isoformat() if r.last_seen else None,
            "tags": [t.name for t in r.tags] if r.tags else [],
        }
        for r in rows
    ]
    
def get_threat_by_id(session: Session, threat_id: str) -> Optional[dict]:
    """
    Retourne le détail complet d'un Threat : métadonnées + IOCs + stats.
    """
    from app.models.threat import Threat

    threat = session.query(Threat).filter(Threat.id == threat_id).first()
    if not threat:
        return None

    indicators = threat.indicators

    # Stats agrégées
    confidences = [i.confidence for i in indicators if i.confidence is not None]
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else None

    # Top tags sur l'ensemble des IOCs du cluster
    tag_counts: dict[str, int] = {}
    for ind in indicators:
        for tag in ind.tags:
            tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1
    top_tags = sorted(tag_counts, key=lambda k: tag_counts[k], reverse=True)[:10]

    # Répartition par type d'IOC
    type_counts: dict[str, int] = {}
    for ind in indicators:
        t = str(ind.type.value if hasattr(ind.type, "value") else ind.type)
        type_counts[t] = type_counts.get(t, 0) + 1

    # Liste des IOCs (50 premiers par confidence)
    sorted_inds = sorted(indicators, key=lambda i: i.confidence or 0, reverse=True)[:50]
    ioc_list = [
        {
            "id": str(i.id),
            "value": i.value,
            "type": str(i.type.value if hasattr(i.type, "value") else i.type),
            "confidence": i.confidence,
            "status": str(i.status.value if hasattr(i.status, "value") else i.status),
            "source": i.source.name if i.source else None,
            "last_seen": i.last_seen.isoformat() if i.last_seen else None,
            "tags": [t.name for t in i.tags],
        }
        for i in sorted_inds
    ]

    return {
        "id": str(threat.id),
        "name": threat.name,
        "threat_type": str(threat.threat_type.value if hasattr(threat.threat_type, "value") else threat.threat_type),
        "description": threat.description,
        "tlp": str(threat.tlp.value if hasattr(threat.tlp, "value") else threat.tlp),
        "created_at": threat.created_at.isoformat() if threat.created_at else None,
        "indicator_count": len(indicators),
        "avg_confidence": avg_confidence,
        "top_tags": top_tags,
        "indicators_by_type": type_counts,
        "indicators": ioc_list,
    }
    
def get_top_sources(session: Session, limit: int = 10) -> list[dict]:
    """Top sources par nombre d'IOCs."""
    rows = (
        session.query(Source.name, func.count(Indicator.id).label("count"))
        .join(Indicator, Indicator.source_id == Source.id)
        .group_by(Source.name)
        .order_by(func.count(Indicator.id).desc())
        .limit(limit)
        .all()
    )
    return [{"name": row.name, "count": int(row.count)} for row in rows]


def get_top_tags(session: Session, limit: int = 10) -> list[dict]:
    """Top tags malware par nombre d'IOCs associés."""
    from app.models.tag import Tag

    rows = (
        session.query(Tag.name, func.count(Indicator.id).label("count"))
        .join(Indicator.tags)
        .filter(Tag.name.like("malware:%"))
        .group_by(Tag.name)
        .order_by(func.count(Indicator.id).desc())
        .limit(limit)
        .all()
    )
    return [{"name": row.name, "count": int(row.count)} for row in rows]


def get_confidence_distribution(session: Session) -> list[dict]:
    """
    Distribution des scores de confiance par tranches de 10.
    Retourne des buckets : 0-9, 10-19, … 90-100.
    """
    from sqlalchemy import case, Integer
    from sqlalchemy import cast

    bucket = (func.floor(Indicator.confidence / 10) * 10).label("bucket")

    rows = (
        session.query(bucket, func.count(Indicator.id).label("count"))
        .filter(Indicator.confidence.isnot(None))
        .filter(Indicator.status == "active")
        .group_by(bucket)
        .order_by(bucket)
        .all()
    )

    return [
        {"range": f"{int(row.bucket)}-{int(row.bucket) + 9}", "count": int(row.count)}
        for row in rows
    ]
    
def create_indicator_manual(session: Session, data: dict) -> dict:
    """
    Crée manuellement un IOC en passant par le pipeline de normalisation.
    Retourne l'indicateur créé ou existant.
    """
    from core.normalize import detect_and_normalize
    from app.persistence import get_or_create_indicator, get_or_create_tag, attach_tag
    from app.models.enums import IOCType

    value = data["value"].strip()
    tlp_str = data.get("tlp", "CLEAR")
    tag_names = data.get("tags", [])
    source_name = data.get("source_name", "Manual Entry")

    # Normalisation
    normalized = detect_and_normalize(value)
    if not normalized:
        raise ValueError(f"Valeur non reconnue comme IOC valide : {value}")

    norm_value, ioc_type_str = normalized
    ioc_type = IOCType(ioc_type_str)
    tlp = TLPLevel[tlp_str] if tlp_str in TLPLevel.__members__ else TLPLevel.CLEAR

    # Source "Manual Entry"
    source = session.query(Source).filter(Source.name == source_name).first()
    if not source:
        source = Source(
            id=uuid4(),
            name=source_name,
            url=None,
            tlp=tlp,
            is_active=True,
        )
        session.add(source)
        session.flush()

    # Création ou récupération de l'indicateur
    ind, created = get_or_create_indicator(
        session,
        value=norm_value,
        ioc_type=ioc_type,
        source_id=source.id,
        tlp=tlp,
    )
    session.flush()

    # Tags additionnels
    # Tags additionnels
    for tag_name in tag_names:
        attach_tag(session, ind, tag_name)

    session.commit()

    return {
        "id": str(ind.id),
        "value": ind.value,
        "type": str(ind.type.value if hasattr(ind.type, "value") else ind.type),
        "status": str(ind.status.value if hasattr(ind.status, "value") else ind.status),
        "confidence": ind.confidence,
        "tlp": str(ind.tlp.value if hasattr(ind.tlp, "value") else ind.tlp),
        "source": source.name,
        "created": created,
    }
    
def get_collection_runs(session: Session, limit: int = 50) -> list[dict]:
    """Retourne les derniers runs de collecte triés par date décroissante."""
    from app.models.collection_run import CollectionRun

    rows = (
        session.query(CollectionRun)
        .join(CollectionRun.source)
        .order_by(CollectionRun.started_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": str(r.id),
            "source": r.source.name if r.source else "—",
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": str(r.status.value if hasattr(r.status, "value") else r.status),
            "items_created": r.items_created,
            "items_updated": r.items_updated,
            "items_errors": r.items_errors,
            "error_message": r.error_message,
            "duration_s": (
                round((r.finished_at - r.started_at).total_seconds())
                if r.finished_at and r.started_at else None
            ),
        }
        for r in rows
    ]

# ─── Cameroun — vue d'ensemble ────────────────────────────────────────────────

def get_cameroon_overview(session: Session) -> dict:
    """Agrège les indicateurs clés de la surveillance Cameroun pour l'Overview
    et la page dédiée : institutions suivies, typosquatting, certificats
    suspects, surface d'attaque exposée.
    """
    total_assets = session.query(MonitoredAsset).filter_by(active=True).count()
    domains_confirmed = (
        session.query(MonitoredAsset)
        .filter_by(active=True, domain_status=DomainStatus.confirmed)
        .count()
    )
    domains_with_candidate = (
        session.query(MonitoredAsset)
        .filter(MonitoredAsset.active.is_(True), MonitoredAsset.domain.isnot(None))
        .count()
    )

    def count_by_tag(tag_name: str) -> int:
        return (
            session.query(Indicator)
            .join(Indicator.tags)
            .filter(Tag.name == tag_name)
            .count()
        )

    typosquat_confirmed = count_by_tag("typosquat:confirmed")
    typosquat_potential = count_by_tag("typosquat:potential")
    ct_findings = count_by_tag("ct-monitor")

    exposed_total = session.query(ExposedAsset).count()
    exposed_high_risk = session.query(ExposedAsset).filter_by(risk_level="high").count()
    exposed_medium_risk = session.query(ExposedAsset).filter_by(risk_level="medium").count()

    return {
        "total_monitored_assets": total_assets,
        "domains_confirmed": domains_confirmed,
        "domains_with_candidate": domains_with_candidate,
        "typosquat_confirmed": typosquat_confirmed,
        "typosquat_potential": typosquat_potential,
        "ct_findings": ct_findings,
        "exposed_total": exposed_total,
        "exposed_high_risk": exposed_high_risk,
        "exposed_medium_risk": exposed_medium_risk,
    }


# ─── Exposed Assets (surface d'attaque) ───────────────────────────────────────

def get_exposed_assets(
    session: Session,
    risk_level: Optional[str] = None,
    monitored_asset_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    """Retourne les IPs exposées, avec le nom de l'institution associée."""
    q = (
        session.query(ExposedAsset, MonitoredAsset.name, MonitoredAsset.acronym)
        .outerjoin(MonitoredAsset, ExposedAsset.monitored_asset_id == MonitoredAsset.id)
    )
    if risk_level:
        q = q.filter(ExposedAsset.risk_level == risk_level)
    if monitored_asset_id:
        q = q.filter(ExposedAsset.monitored_asset_id == monitored_asset_id)

    from sqlalchemy import case

    risk_order = case(
        (ExposedAsset.risk_level == "high", 0),
        (ExposedAsset.risk_level == "medium", 1),
        else_=2,
    )

    total = q.count()
    rows = (
        q.order_by(risk_order, ExposedAsset.last_seen.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for asset, asset_name, acronym in rows:
        items.append({
            "id": str(asset.id),
            "ip_address": asset.ip_address,
            "institution_name": asset_name,
            "institution_acronym": acronym,
            "hostnames": asset.hostnames or [],
            "ports": asset.ports or [],
            "cpes": asset.cpes or [],
            "vulns": asset.vulns or [],
            "tags": asset.tags or [],
            "risk_level": asset.risk_level,
            "first_seen": asset.first_seen,
            "last_seen": asset.last_seen,
        })
    return items, total


# ─── Monitored Assets (institutions surveillées) ──────────────────────────────

def get_monitored_assets(
    session: Session,
    category: Optional[str] = None,
) -> list[dict]:
    """Retourne la liste des institutions surveillées (174 au total, pas de pagination)."""
    q = session.query(MonitoredAsset).filter_by(active=True)
    if category:
        q = q.filter(MonitoredAsset.category == category)

    assets = q.order_by(MonitoredAsset.category, MonitoredAsset.name).all()

    return [
        {
            "id": str(a.id),
            "name": a.name,
            "acronym": a.acronym,
            "category": a.category.value,
            "domain": a.domain,
            "domain_status": a.domain_status.value,
            "asn": a.asn,
        }
        for a in assets
    ]


def report_false_positive(
    session: Session,
    indicator_id: str,
    monitored_asset_id: Optional[str] = None,
) -> dict:
    """
    Marque un IOC typosquat/CT comme faux positif :
    - status -> whitelisted (jamais de suppression)
    - retrait des tags typosquat/ct trompeurs
    - cameroon_relevance remis à 0
    - si monitored_asset_id fourni : ajoute la valeur comme alias connu
      de cette institution, pour que les futurs scans l'excluent automatiquement
    """
    from app.models.enums import IndicatorStatus

    indicator = session.query(Indicator).filter_by(id=indicator_id).first()
    if not indicator:
        raise ValueError(f"Indicator {indicator_id} introuvable")

    false_positive_tags = {
        "typosquat", "typosquat:confirmed", "typosquat:potential",
        "ct-monitor", "ct:confirmed", "ct:potential",
    }
    removed_tags = [t.name for t in indicator.tags if t.name in false_positive_tags]

    indicator.status = IndicatorStatus.whitelisted
    indicator.tags = [t for t in indicator.tags if t.name not in false_positive_tags]
    indicator.cameroon_relevance = 0

    alias_added = False
    if monitored_asset_id:
        asset = session.query(MonitoredAsset).filter_by(id=monitored_asset_id).first()
        if asset:
            aliases = list(asset.known_aliases or [])
            if indicator.value.lower() not in [a.lower() for a in aliases]:
                aliases.append(indicator.value)
                asset.known_aliases = aliases
                alias_added = True

    session.commit()

    return {
        "indicator_id": str(indicator.id),
        "value": indicator.value,
        "status": indicator.status.value,
        "removed_tags": removed_tags,
        "alias_added": alias_added,
    }


def get_cameroon_timeline(session: Session, days: int = 30) -> list[dict]:
    """
    Nouvelles détections Cameroun par jour, sur les N derniers jours :
    typosquatting, certificats suspects, IPs exposées.
    Permet de visualiser si la pression monte dans le temps.
    """
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)

    typosquat_counts = dict(
        session.query(
            func.date(Indicator.created_at),
            func.count(Indicator.id),
        )
        .join(Indicator.tags)
        .filter(Tag.name == "typosquat", Indicator.created_at >= since)
        .group_by(func.date(Indicator.created_at))
        .all()
    )

    ct_counts = dict(
        session.query(
            func.date(Indicator.created_at),
            func.count(Indicator.id),
        )
        .join(Indicator.tags)
        .filter(Tag.name == "ct-monitor", Indicator.created_at >= since)
        .group_by(func.date(Indicator.created_at))
        .all()
    )

    exposed_counts = dict(
        session.query(
            func.date(ExposedAsset.first_seen),
            func.count(ExposedAsset.id),
        )
        .filter(ExposedAsset.first_seen >= since)
        .group_by(func.date(ExposedAsset.first_seen))
        .all()
    )

    all_dates = sorted(set(typosquat_counts) | set(ct_counts) | set(exposed_counts))

    return [
        {
            "date": str(d),
            "typosquat": typosquat_counts.get(d, 0),
            "ct_monitor": ct_counts.get(d, 0),
            "exposed_assets": exposed_counts.get(d, 0),
        }
        for d in all_dates
    ]


def get_institutions_ranked(session: Session) -> list[dict]:
    """
    Classe les institutions par score de risque composite :
    typosquats confirmés (poids 3) + IPs haut risque exposées (poids 3)
    + IPs risque moyen (poids 1) + certificats suspects (poids 2).
    """
    assets = session.query(MonitoredAsset).filter_by(active=True).all()

    # Compte les IOCs typosquat/ct par institution via le tag typosquat:{acronym}
    tag_rows = (
        session.query(Tag.name, func.count(Indicator.id))
        .join(Indicator.tags)
        .filter(Tag.name.like("typosquat:%") | Tag.name.like("ct:%"))
        .filter(Tag.name.notin_(["typosquat:confirmed", "typosquat:potential", "ct:confirmed", "ct:potential"]))
        .group_by(Tag.name)
        .all()
    )
    tag_counts: dict[str, int] = {name: count for name, count in tag_rows}

    exposed_rows = (
        session.query(
            ExposedAsset.monitored_asset_id,
            ExposedAsset.risk_level,
            func.count(ExposedAsset.id),
        )
        .filter(ExposedAsset.monitored_asset_id.isnot(None))
        .group_by(ExposedAsset.monitored_asset_id, ExposedAsset.risk_level)
        .all()
    )
    exposed_by_asset: dict[str, dict[str, int]] = {}
    for asset_id, risk, count in exposed_rows:
        exposed_by_asset.setdefault(str(asset_id), {})[risk] = count

    results = []
    for a in assets:
        key = (a.acronym or a.name[:20]).lower().replace(" ", "_")
        typosquat_hits = tag_counts.get(f"typosquat:{key}", 0)
        ct_hits = tag_counts.get(f"ct:{key}", 0)
        exposure = exposed_by_asset.get(str(a.id), {})
        high = exposure.get("high", 0)
        medium = exposure.get("medium", 0)

        score = typosquat_hits * 3 + high * 3 + medium * 1 + ct_hits * 2

        if score == 0:
            continue  # on n'affiche que les institutions avec un signal réel

        results.append({
            "id": str(a.id),
            "name": a.name,
            "acronym": a.acronym,
            "category": a.category.value,
            "typosquat_findings": typosquat_hits,
            "ct_findings": ct_hits,
            "exposed_high_risk": high,
            "exposed_medium_risk": medium,
            "risk_score": score,
        })

    results.sort(key=lambda r: r["risk_score"], reverse=True)
    return results


def get_vuln_severity_breakdown(session: Session) -> dict:
    """
    Croise les CVE exposées (table exposed_assets) avec les scores CVSS
    déjà collectés via le collecteur NVD, pour distinguer une CVE critique
    d'une CVE mineure plutôt que de simplement compter les CVE.
    """
    assets = session.query(ExposedAsset.vulns).filter(ExposedAsset.vulns.isnot(None)).all()

    cve_occurrences: dict[str, int] = {}
    for (vulns,) in assets:
        for cve_id in (vulns or []):
            cve_occurrences[cve_id] = cve_occurrences.get(cve_id, 0) + 1

    if not cve_occurrences:
        return {
            "critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0,
            "distinct_cves": 0, "total_occurrences": 0,
        }

    cve_rows = (
        session.query(Indicator.value, Indicator.raw_metadata)
        .filter(Indicator.type == "cve", Indicator.value.in_(list(cve_occurrences.keys())))
        .all()
    )
    cvss_scores: dict[str, float] = {}
    for value, metadata in cve_rows:
        score = (metadata or {}).get("cvss_score")
        if score is not None:
            try:
                cvss_scores[value] = float(score)
            except (ValueError, TypeError):
                pass

    buckets = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
    for cve_id, occurrences in cve_occurrences.items():
        score = cvss_scores.get(cve_id)
        if score is None:
            buckets["unknown"] += occurrences
        elif score >= 9.0:
            buckets["critical"] += occurrences
        elif score >= 7.0:
            buckets["high"] += occurrences
        elif score >= 4.0:
            buckets["medium"] += occurrences
        else:
            buckets["low"] += occurrences

    return {
        **buckets,
        "distinct_cves": len(cve_occurrences),
        "total_occurrences": sum(cve_occurrences.values()),
    }


def create_monitored_asset(session: Session, data: dict) -> dict:
    """Crée une nouvelle institution surveillée."""
    from app.models.enums import AssetCategory, DomainStatus

    asset = MonitoredAsset(
        id=uuid4(),
        name=data["name"],
        acronym=data.get("acronym"),
        category=AssetCategory(data["category"]),
        domain=data.get("domain"),
        domain_status=DomainStatus(data.get("domain_status", "unconfirmed")),
        asn=data.get("asn"),
        known_aliases=data.get("known_aliases", []),
    )
    session.add(asset)
    session.commit()
    return {
        "id": str(asset.id),
        "name": asset.name,
        "acronym": asset.acronym,
        "category": asset.category.value,
        "domain": asset.domain,
        "domain_status": asset.domain_status.value,
        "asn": asset.asn,
    }


def update_monitored_asset(session: Session, asset_id: str, data: dict) -> dict:
    """Met à jour une institution surveillée (champs partiels acceptés)."""
    from app.models.enums import AssetCategory, DomainStatus

    asset = session.query(MonitoredAsset).filter_by(id=asset_id).first()
    if not asset:
        raise ValueError(f"MonitoredAsset {asset_id} introuvable")

    if "name" in data and data["name"] is not None:
        asset.name = data["name"]
    if "acronym" in data:
        asset.acronym = data["acronym"]
    if "category" in data and data["category"] is not None:
        asset.category = AssetCategory(data["category"])
    if "domain" in data:
        asset.domain = data["domain"]
    if "domain_status" in data and data["domain_status"] is not None:
        asset.domain_status = DomainStatus(data["domain_status"])
    if "asn" in data:
        asset.asn = data["asn"]
    if "known_aliases" in data and data["known_aliases"] is not None:
        asset.known_aliases = data["known_aliases"]
    if "active" in data and data["active"] is not None:
        asset.active = data["active"]

    session.commit()
    return {
        "id": str(asset.id),
        "name": asset.name,
        "acronym": asset.acronym,
        "category": asset.category.value,
        "domain": asset.domain,
        "domain_status": asset.domain_status.value,
        "asn": asset.asn,
    }


def get_sector_breakdown(session: Session) -> list[dict]:
    """
    Agrège le risque par secteur d'institution (ministère, banque, télécom,
    société publique, institution) — pour visualiser quel secteur est le
    plus exposé globalement, pas juste institution par institution.
    """
    assets = session.query(MonitoredAsset).filter_by(active=True).all()

    tag_rows = (
        session.query(Tag.name, func.count(Indicator.id))
        .join(Indicator.tags)
        .filter(Tag.name.like("typosquat:%"))
        .filter(Tag.name.notin_(["typosquat:confirmed", "typosquat:potential"]))
        .group_by(Tag.name)
        .all()
    )
    tag_counts: dict[str, int] = {name: count for name, count in tag_rows}

    exposed_rows = (
        session.query(
            ExposedAsset.monitored_asset_id,
            ExposedAsset.risk_level,
            func.count(ExposedAsset.id),
        )
        .filter(ExposedAsset.monitored_asset_id.isnot(None))
        .group_by(ExposedAsset.monitored_asset_id, ExposedAsset.risk_level)
        .all()
    )
    exposed_by_asset: dict[str, dict[str, int]] = {}
    for asset_id, risk, count in exposed_rows:
        exposed_by_asset.setdefault(str(asset_id), {})[risk] = count

    sectors: dict[str, dict] = {}
    for a in assets:
        cat = a.category.value
        if cat not in sectors:
            sectors[cat] = {
                "category": cat,
                "institution_count": 0,
                "typosquat_findings": 0,
                "exposed_high_risk": 0,
                "exposed_medium_risk": 0,
                "domains_confirmed": 0,
            }
        sectors[cat]["institution_count"] += 1

        key = (a.acronym or a.name[:20]).lower().replace(" ", "_")
        sectors[cat]["typosquat_findings"] += tag_counts.get(f"typosquat:{key}", 0)

        exposure = exposed_by_asset.get(str(a.id), {})
        sectors[cat]["exposed_high_risk"] += exposure.get("high", 0)
        sectors[cat]["exposed_medium_risk"] += exposure.get("medium", 0)

        if a.domain_status.value == "confirmed":
            sectors[cat]["domains_confirmed"] += 1

    return sorted(sectors.values(), key=lambda s: s["exposed_high_risk"] + s["typosquat_findings"], reverse=True)


def get_top_exposed_ports(session: Session, limit: int = 10) -> list[dict]:
    """
    Ports les plus fréquemment exposés sur la surface d'attaque — pour
    repérer les tendances (ex: beaucoup de RDP/MySQL ouverts).
    """
    assets = session.query(ExposedAsset.ports).filter(ExposedAsset.ports.isnot(None)).all()

    port_counts: dict[int, int] = {}
    for (ports,) in assets:
        for p in (ports or []):
            port_counts[p] = port_counts.get(p, 0) + 1

    top = sorted(port_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"port": p, "count": c} for p, c in top]
