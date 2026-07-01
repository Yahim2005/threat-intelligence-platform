# api/schemas.py

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ─── Indicator ───────────────────────────────────────────────────────────────

class IndicatorResponse(BaseModel):
    id: str                        # UUID sérialisé en string
    value: str
    type: str
    status: str
    confidence: Optional[int]      # 0-100, s'appelle confidence en base
    tlp: Optional[str]
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    source: Optional[str]          # nom de la source (FK simple)
    tags: list[str]
    attack_techniques: list[str]

    model_config = {"from_attributes": True}


class IndicatorListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[IndicatorResponse]


# ─── Source ───────────────────────────────────────────────────────────────────

class SourceResponse(BaseModel):
    id: str
    name: str
    url: Optional[str]
    tlp: Optional[str]
    is_active: bool
    indicator_count: int

    model_config = {"from_attributes": True}


# ─── Threat ───────────────────────────────────────────────────────────────────

class ThreatResponse(BaseModel):
    id: str
    name: str
    indicator_count: int
    avg_confidence: Optional[float]
    top_tags: list[str]

    model_config = {"from_attributes": True}


# ─── Stats ────────────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_indicators: int
    active_indicators: int
    expired_indicators: int
    whitelisted_indicators: int
    total_threats: int
    total_sources: int
    avg_confidence: Optional[float]
    indicators_by_type: dict[str, int]
    indicators_by_tlp: dict[str, int]
    
# ─── Analytics ────────────────────────────────────────────────────────────────

class RelatedIndicatorResponse(BaseModel):
    value: str
    type: str
    confidence: Optional[int]
    status: str
    relationship_type: str
    relationship_confidence: int
    rule: Optional[str]

class TimelinePointResponse(BaseModel):
    date: str        # "2026-06-15"
    sightings: int

class TrendPointResponse(BaseModel):
    date: str        # "2026-06-15"
    count: int
    
class AlertResponse(BaseModel):
    id: str
    value: str
    type: str
    confidence: int
    source: Optional[str]
    last_seen: Optional[str]
    tags: list[str]
    
class ThreatIndicatorResponse(BaseModel):
    id: str
    value: str
    type: str
    confidence: Optional[int]
    status: str
    source: Optional[str]
    last_seen: Optional[str]
    tags: list[str]

class ThreatDetailResponse(BaseModel):
    id: str
    name: str
    threat_type: str
    description: Optional[str]
    tlp: str
    created_at: Optional[str]
    indicator_count: int
    avg_confidence: Optional[float]
    top_tags: list[str]
    indicators_by_type: dict[str, int]
    indicators: list[ThreatIndicatorResponse]
    
class NameCountResponse(BaseModel):
    name: str
    count: int

class RangeCountResponse(BaseModel):
    range: str
    count: int
    
class IndicatorCreate(BaseModel):
    value: str
    type: Optional[str] = None        # auto-détecté si absent
    tlp: str = "CLEAR"
    tags: list[str] = []
    source_name: str = "Manual Entry"