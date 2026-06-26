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
