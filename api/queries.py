# api/queries.py

from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Indicator, Source, Tag, Threat


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

    total = q.count()
    # nouveau
    items = (
        q.order_by(Indicator.confidence.desc().nulls_last(), Indicator.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()  
    )
    return items, total


def get_indicator_by_value(session: Session, value: str) -> Optional[Indicator]:
    return session.query(Indicator).filter(Indicator.value == value).first()


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
                tag_counts[tag.slug] = tag_counts.get(tag.slug, 0) + 1
        top_tags = sorted(tag_counts, key=lambda k: tag_counts[k], reverse=True)[:5]

        results.append({
            "id": str(threat.id),
            "name": threat.name,
            "indicator_count": len(indicators),
            "avg_confidence": round(avg_confidence, 2) if avg_confidence is not None else None,
            "top_tags": top_tags,
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
