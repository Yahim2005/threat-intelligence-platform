# api/main.py

from __future__ import annotations
from dotenv import load_dotenv

from app.models import user
load_dotenv()
from uuid import uuid4

from app.models.user import User
from app.models.enums import UserRole
from app.security import hash_password, verify_password, create_access_token
from api.auth import get_current_user, require_admin
import time
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal
from app.logger import setup_logging, get_logger
from app.models import Indicator
from api import queries, schemas, exports

# ─── Logging : doit être configuré en premier ─────────────────────────────────

setup_logging(log_level="INFO")
logger = get_logger("api")

# ─── Rate limiter ─────────────────────────────────────────────────────────────
# get_remote_address : identifie chaque client par son IP

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ─── Métriques en mémoire ─────────────────────────────────────────────────────
# Simple dict de compteurs — remis à zéro au redémarrage.
# Pour de la prod réelle on utiliserait Prometheus, mais ici on garde simple.

_metrics: dict = {
    "requests_total": 0,
    "requests_4xx": 0,
    "requests_5xx": 0,
    "requests_by_path": defaultdict(int),
    "latency_total_ms": 0.0,
}

# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Threat Intelligence Platform",
    description="API REST pour accéder aux IOCs, sources, threats et statistiques.",
    version="1.0.0",
)

# Branche le handler d'erreur 429 de slowapi sur l'app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ─── CORS ────────────────────────────────────────────────────────────────────
import os as _os
_origins = _os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(exports.router)


# ─── Middleware : log + métriques de chaque requête ───────────────────────────

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    S'exécute autour de chaque requête HTTP.
    - Mesure la latence
    - Loggue méthode / path / status / durée
    - Incrémente les compteurs de métriques
    """
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    # Mise à jour des métriques
    _metrics["requests_total"] += 1
    _metrics["requests_by_path"][request.url.path] += 1
    _metrics["latency_total_ms"] += duration_ms

    if 400 <= response.status_code < 500:
        _metrics["requests_4xx"] += 1
    elif response.status_code >= 500:
        _metrics["requests_5xx"] += 1

    # Log structuré JSON
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 2),
        client=request.client.host if request.client else "unknown",
    )

    return response


# ─── Dépendance DB ────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _str_enum(val) -> Optional[str]:
    """Convertit un enum SQLAlchemy en string propre."""
    if val is None:
        return None
    return val.value if hasattr(val, "value") else str(val)


def _serialize_indicator(ind: Indicator) -> schemas.IndicatorResponse:
    # Extraction GeoIP depuis les enrichissements
    geoip = None
    if hasattr(ind, "enrichments") and ind.enrichments:
        for e in ind.enrichments:
            if e.provider == "geoip" and e.data:
                geoip = schemas.GeoIPData(
                    country_code=e.data.get("country_code"),
                    country_name=e.data.get("country_name"),
                    city=e.data.get("city"),
                    latitude=e.data.get("latitude"),
                    longitude=e.data.get("longitude"),
                    asn=e.data.get("asn"),
                    asn_org=e.data.get("asn_org"),
                )
                break

    # Score breakdown depuis raw_metadata
    score_breakdown = None
    if ind.raw_metadata and "score_components" in ind.raw_metadata:
        components = ind.raw_metadata["score_components"]
        weights = {
            "source_reliability": 0.22,
            "corroboration":      0.18,
            "source_diversity":   0.17,
            "type_bonus":         0.16,
            "recency":            0.14,
            "malware_tag_bonus":  0.08,
            "external_reputation": 0.05,
        }
        score_breakdown = {
            k: {
                "value":       round(v, 4),
                "weight":      weights.get(k, 0),
                "contribution": round(v * weights.get(k, 0) * 100, 1),
            }
            for k, v in components.items()
        }

    return schemas.IndicatorResponse(
        id=str(ind.id),
        value=ind.value,
        type=_str_enum(ind.type),
        status=_str_enum(ind.status),
        confidence=ind.confidence,
        tlp=_str_enum(ind.tlp),
        first_seen=ind.first_seen,
        last_seen=ind.last_seen,
        source=ind.source.name if ind.source else None,
        tags=[t.name for t in ind.tags] if ind.tags else [],
        attack_techniques=[
            m.technique_id for m in ind.attack_mappings
        ] if hasattr(ind, "attack_mappings") and ind.attack_mappings else [],
        geoip=geoip,
        score_breakdown=score_breakdown,
    )


def _serialize_user(user: User) -> schemas.UserResponse:
    return schemas.UserResponse(
        id=str(user.id),
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
    )


# ─── Routes : Observabilité ───────────────────────────────────────────────────

@app.get("/health", tags=["Observability"])
def health_check(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Vérifie que l'API et la base de données sont opérationnelles.
    Répond 200 si tout va bien, 503 si la DB est inaccessible.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.error("health_check_db_failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "db": "unreachable", "error": str(exc)},
        )

    logger.info("health_check", db=db_status)
    return {"status": "ok", "db": db_status, "version": app.version}


@app.get("/metrics", tags=["Observability"])
def get_metrics():
    """
    Retourne les compteurs internes de l'API.
    Remis à zéro au redémarrage — pas de persistance.
    """
    total = _metrics["requests_total"]
    avg_latency = (
        round(_metrics["latency_total_ms"] / total, 2) if total > 0 else 0.0
    )
    return {
        "requests_total": total,
        "requests_4xx": _metrics["requests_4xx"],
        "requests_5xx": _metrics["requests_5xx"],
        "avg_latency_ms": avg_latency,
        "requests_by_path": dict(_metrics["requests_by_path"]),
    }

@app.post("/indicators", response_model=schemas.IndicatorResponse, tags=["Indicators"])
@limiter.limit("30/minute")
def submit_indicator(
    request: Request,
    body: schemas.IndicatorCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    Soumet manuellement un IOC dans la plateforme.
    La valeur est normalisée et le type auto-détecté si non fourni.
    """
    try:
        result = queries.create_indicator_manual(db, body.model_dump())
        ind = queries.get_indicator_by_value(db, result["value"])
        if ind:
            return _serialize_indicator(ind)
        raise HTTPException(status_code=500, detail="Erreur lors de la création.")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("submit_indicator_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ─── Routes : Auth ─────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=schemas.TokenResponse, tags=["Auth"])
@limiter.limit("10/minute")
def register(
    request: Request,
    body: schemas.UserRegister,
    db: Session = Depends(get_db),
):
    """
    Crée un nouveau compte utilisateur (rôle 'user' par défaut).
    """
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé.")

    if body.phone:
        existing_phone = db.query(User).filter(User.phone == body.phone).first()
        if existing_phone:
            raise HTTPException(status_code=409, detail="Ce numéro est déjà utilisé.")

    user = User(
        id=uuid4(),
        email=body.email,
        phone=body.phone,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.TokenResponse(
        access_token=token,
        user=_serialize_user(user),
    )


@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["Auth"])
@limiter.limit("10/minute")
def login(
    request: Request,
    body: schemas.UserLogin,
    db: Session = Depends(get_db),
):
    """
    Connexion via email OU téléphone + mot de passe.
    """
    user = (
        db.query(User)
        .filter(
            (User.email == body.identifier) | (User.phone == body.identifier)
        )
        .first()
    )

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé.")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.TokenResponse(
        access_token=token,
        user=_serialize_user(user),
    )


@app.get("/auth/me", response_model=schemas.UserResponse, tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    return _serialize_user(current_user)

# ─── Routes : Indicators ──────────────────────────────────────────────────────

@app.get("/indicators", response_model=schemas.IndicatorListResponse, tags=["Indicators"])
@limiter.limit("60/minute")
def list_indicators(
    request: Request,
    type: Optional[str] = Query(None, description="Type : ip, domain, url, sha256, cve…"),
    status: Optional[str] = Query(None, description="Statut : active, expired, whitelisted"),
    confidence_min: Optional[int] = Query(None, ge=0, le=100, description="Confidence minimum"),
    confidence_max: Optional[int] = Query(None, ge=0, le=100, description="Confidence maximum"),
    source: Optional[str] = Query(None, description="Nom exact de la source"),
    tag: Optional[str] = Query(None, description="Slug du tag, ex: malware:emotet"),
    tlp: Optional[str] = Query(None, description="Niveau TLP : CLEAR, GREEN, AMBER, RED"),
    search: Optional[str] = Query(None, description="Recherche partielle dans la valeur de l'IOC"),
    cameroon: Optional[bool] = Query(None, description="Filtrer les IOCs pertinents pour le Cameroun"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    items, total = queries.get_indicators(
        session=db,
        ioc_type=type,
        status=status,
        confidence_min=confidence_min,
        confidence_max=confidence_max,
        source_name=source,
        tag_slug=tag,
        tlp=tlp,
        search=search,
        cameroon=cameroon,
        page=page,
        page_size=page_size,
    )
    return schemas.IndicatorListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_serialize_indicator(i) for i in items],
    )

# ─── Routes : Analytics ───────────────────────────────────────────────────────

@app.get("/indicators/{value:path}/related", response_model=list[schemas.RelatedIndicatorResponse], tags=["Analytics"])
@limiter.limit("60/minute")
def get_related(value: str, request: Request, db: Session = Depends(get_db)):
    """
    Retourne les IOCs liés à `value` via le graphe de corrélation.
    Utile pour comprendre le contexte d'un indicateur : 
    ex. une IP peut être liée à des domaines qu'elle résout, ou à des IOCs du même batch.
    """
    results = queries.get_related_indicators(db, value)
    return [schemas.RelatedIndicatorResponse(**r) for r in results]


@app.get("/indicators/{value:path}/timeline", response_model=list[schemas.TimelinePointResponse], tags=["Analytics"])
@limiter.limit("60/minute")
def get_timeline(
    value: str,
    request: Request,
    days: int = Query(30, ge=1, le=90, description="Nombre de jours d'historique"),
    db: Session = Depends(get_db),
):
    """
    Retourne l'historique de sightings par jour pour un indicateur.
    Permet de voir si une menace est récente ou persistante dans le temps.
    """
    results = queries.get_indicator_timeline(db, value, days=days)
    return [schemas.TimelinePointResponse(**r) for r in results]


@app.get("/indicators/{value:path}", response_model=schemas.IndicatorResponse, tags=["Indicators"])
@limiter.limit("60/minute")
def get_indicator(value: str, request: Request, db: Session = Depends(get_db)):
    """Récupère un indicateur par sa valeur exacte."""
    ind = queries.get_indicator_by_value(db, value)
    if not ind:
        raise HTTPException(status_code=404, detail=f"Indicateur '{value}' introuvable.")
    return _serialize_indicator(ind)
# ─── Routes : Sources ─────────────────────────────────────────────────────────


# ─── Routes : Sources ─────────────────────────────────────────────────────────

@app.get("/sources", response_model=list[schemas.SourceResponse], tags=["Sources"])
@limiter.limit("60/minute")
def list_sources(request: Request, db: Session = Depends(get_db)):
    rows = queries.get_sources(db)
    return [
        schemas.SourceResponse(
            id=str(source.id),
            name=source.name,
            url=source.url,
            tlp=_str_enum(source.tlp),
            is_active=source.is_active,
            indicator_count=count,
        )
        for source, count in rows
    ]

@app.get("/threats/{threat_id}", response_model=schemas.ThreatDetailResponse, tags=["Threats"])
@limiter.limit("60/minute")
def get_threat(threat_id: str, request: Request, db: Session = Depends(get_db)):
    """Retourne le détail complet d'un cluster de menaces."""
    result = queries.get_threat_by_id(db, threat_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Threat '{threat_id}' introuvable.")
    return schemas.ThreatDetailResponse(**result)


# ─── Routes : Threats ─────────────────────────────────────────────────────────

@app.get("/threats", response_model=list[schemas.ThreatResponse], tags=["Threats"])
@limiter.limit("60/minute")
def list_threats(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    results, total = queries.get_threats(db, page=page, page_size=page_size)
    return [schemas.ThreatResponse(**r) for r in results]

# ─── Routes : Alerts ──────────────────────────────────────────────────────────

@app.get("/alerts", response_model=list[schemas.AlertResponse], tags=["Alerts"])
@limiter.limit("60/minute")
def get_alerts(
    request: Request,
    threshold: int = Query(75, ge=0, le=100, description="Score minimum de confiance"),
    hours: int = Query(24, ge=1, le=720, description="Fenêtre temporelle en heures (max 30 jours)"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retourne les IOCs actifs haute confiance vus récemment.
    Utilisé par le panneau d'alertes du dashboard.
    """
    results = queries.get_alerts(db, threshold=threshold, hours=hours, limit=limit)
    return [schemas.AlertResponse(**r) for r in results]

# ─── Routes : Analytics avancée ───────────────────────────────────────────────

@app.get("/analytics/top-sources", response_model=list[schemas.NameCountResponse], tags=["Analytics"])
@limiter.limit("60/minute")
def get_top_sources(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Top sources par volume d'IOCs."""
    return queries.get_top_sources(db, limit=limit)


@app.get("/analytics/top-tags", response_model=list[schemas.NameCountResponse], tags=["Analytics"])
@limiter.limit("60/minute")
def get_top_tags(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Top tags malware par nombre d'IOCs."""
    return queries.get_top_tags(db, limit=limit)


@app.get("/analytics/confidence-distribution", response_model=list[schemas.RangeCountResponse], tags=["Analytics"])
@limiter.limit("60/minute")
def get_confidence_distribution(
    request: Request,
    db: Session = Depends(get_db),
):
    """Distribution des scores de confiance par tranches de 10."""
    return queries.get_confidence_distribution(db)

@app.get("/collection-runs", response_model=list[schemas.CollectionRunResponse], tags=["Observability"])
@limiter.limit("60/minute")
def get_collection_runs(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retourne l'historique des runs de collecte."""
    return queries.get_collection_runs(db, limit=limit)

# ─── Routes : Stats ───────────────────────────────────────────────────────────

@app.get("/stats/trends", response_model=list[schemas.TrendPointResponse], tags=["Analytics"])
@limiter.limit("60/minute")
def get_trends(
    request: Request,
    days: int = Query(30, ge=1, le=90, description="Nombre de jours"),
    db: Session = Depends(get_db),
):
    """
    Retourne le volume d'IOCs ingérés par jour sur les N derniers jours.
    Alimente le graphe de tendance du dashboard.
    """
    results = queries.get_ingestion_trends(db, days=days)
    return [schemas.TrendPointResponse(**r) for r in results]


@app.get("/stats", response_model=schemas.StatsResponse, tags=["Stats"])
@limiter.limit("60/minute")
def get_stats(request: Request, db: Session = Depends(get_db)):
    return schemas.StatsResponse(**queries.get_stats(db))

# ─── Routes : Cameroun ─────────────────────────────────────────────────────────
@app.get("/cameroon/overview", response_model=schemas.CameroonOverviewResponse, tags=["Cameroon"])
@limiter.limit("60/minute")
def get_cameroon_overview(request: Request, db: Session = Depends(get_db)):
    """
    Vue d'ensemble de la surveillance Cameroun : institutions suivies,
    typosquatting détecté, certificats suspects, surface d'attaque exposée.
    """
    return schemas.CameroonOverviewResponse(**queries.get_cameroon_overview(db))


@app.get("/exposed-assets", response_model=schemas.ExposedAssetListResponse, tags=["Cameroon"])
@limiter.limit("60/minute")
def list_exposed_assets(
    request: Request,
    risk_level: Optional[str] = Query(None, description="Filtrer par niveau : high, medium, info"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Retourne les IPs camerounaises avec des services exposés,
    détectées via Shodan InternetDB. Trié par niveau de risque.
    """
    items, total = queries.get_exposed_assets(db, risk_level=risk_level, page=page, page_size=page_size)
    return schemas.ExposedAssetListResponse(
        total=total, page=page, page_size=page_size,
        items=[schemas.ExposedAssetResponse(**i) for i in items],
    )


@app.get("/monitored-assets", response_model=list[schemas.MonitoredAssetResponse], tags=["Cameroon"])
@limiter.limit("60/minute")
def list_monitored_assets(
    request: Request,
    category: Optional[str] = Query(None, description="ministry, bank, telecom, public_company, institution"),
    db: Session = Depends(get_db),
):
    """Retourne la liste des institutions camerounaises surveillées."""
    return [schemas.MonitoredAssetResponse(**a) for a in queries.get_monitored_assets(db, category=category)]
