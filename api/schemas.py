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
    metadata: Optional[dict] = None
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
    cameroon_relevance: int = 0
    institution: Optional[str] = None
    mechanism_counts: dict[str, int] = {}
    exposed_ip_count: int = 0
    first_seen: Optional[str] = None

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
    institution: Optional[str] = None
    mechanism_counts: dict[str, int] = {}
    exposed_ips: list[str] = []
    first_seen: Optional[str] = None
    
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

# ─── Cameroun ──────────────────────────────────────────────────────────────

class CameroonOverviewResponse(BaseModel):
    total_monitored_assets: int
    domains_confirmed: int
    domains_with_candidate: int
    typosquat_confirmed: int
    typosquat_potential: int
    ct_findings: int
    exposed_total: int
    exposed_high_risk: int
    exposed_medium_risk: int


# ─── Exposed Assets / Monitored Assets ────────────────────────────────────────

class ExposedAssetResponse(BaseModel):
    id: str
    ip_address: str
    institution_name: Optional[str]
    institution_acronym: Optional[str]
    hostnames: list[str]
    ports: list[int]
    cpes: list[str]
    vulns: list[str]
    tags: list[str]
    risk_level: str
    first_seen: datetime
    last_seen: datetime


class ExposedAssetListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ExposedAssetResponse]


class MonitoredAssetResponse(BaseModel):
    id: str
    name: str
    acronym: Optional[str]
    category: str
    domain: Optional[str]
    domain_status: str
    asn: Optional[int]
    verification_note: Optional[str] = None


class FalsePositiveRequest(BaseModel):
    indicator_id: str
    monitored_asset_id: Optional[str] = None


class FalsePositiveResponse(BaseModel):
    indicator_id: str
    value: str
    status: str
    removed_tags: list[str]
    alias_added: bool


class CameroonTimelinePointResponse(BaseModel):
    date: str
    typosquat: int
    ct_monitor: int
    exposed_assets: int


class InstitutionRiskResponse(BaseModel):
    id: str
    name: str
    acronym: Optional[str]
    category: str
    typosquat_findings: int
    ct_findings: int
    exposed_high_risk: int
    exposed_medium_risk: int
    risk_score: int


class VulnSeverityResponse(BaseModel):
    critical: int
    high: int
    medium: int
    low: int
    unknown: int
    distinct_cves: int
    total_occurrences: int


class MonitoredAssetCreate(BaseModel):
    name: str
    acronym: Optional[str] = None
    category: str
    domain: Optional[str] = None
    domain_status: Optional[str] = "unconfirmed"
    asn: Optional[int] = None
    known_aliases: Optional[list[str]] = []


class MonitoredAssetUpdate(BaseModel):
    name: Optional[str] = None
    acronym: Optional[str] = None
    category: Optional[str] = None
    domain: Optional[str] = None
    domain_status: Optional[str] = None
    asn: Optional[int] = None
    known_aliases: Optional[list[str]] = None
    active: Optional[bool] = None


class SectorBreakdownResponse(BaseModel):
    category: str
    institution_count: int
    typosquat_findings: int
    exposed_high_risk: int
    exposed_medium_risk: int
    domains_confirmed: int


class PortCountResponse(BaseModel):
    port: int
    count: int


# ─── Clients API (organismes partenaires) ────────────────────────────────────

class ApiClientCreate(BaseModel):
    name: str
    contact_email: Optional[str] = None


class ApiClientResponse(BaseModel):
    id: str
    name: str
    contact_email: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ApiClientCreateResponse(ApiClientResponse):
    api_key: str


# ─── Destinataires du digest email ────────────────────────────────────────────

class EmailRecipientCreate(BaseModel):
    name: str
    email: str


class EmailRecipientResponse(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
