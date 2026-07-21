# api/schemas.py

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ─── Indicator ───────────────────────────────────────────────────────────────

class IndicatorResponse(BaseModel):
    id: str
    value: str
    type: str
    status: str
    confidence: Optional[int]
    tlp: Optional[str]
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    source: Optional[str]
    tags: list[str]
    attack_techniques: list[str]
    geoip: Optional[GeoIPData] = None
    score_breakdown: Optional[dict] = None
    cameroon_relevance: int = 0
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
    
class GeoIPData(BaseModel):
    country_code: Optional[str]
    country_name: Optional[str]
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    asn: Optional[int]
    asn_org: Optional[str]
    
class CollectionRunResponse(BaseModel):
    id: str
    source: str
    started_at: Optional[str]
    finished_at: Optional[str]
    status: str
    items_created: int
    items_updated: int
    items_errors: int
    error_message: Optional[str]
    duration_s: Optional[int]


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    full_name: Optional[str] = None
    password: str


class UserLogin(BaseModel):
    identifier: str  # email OU téléphone
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    phone: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
