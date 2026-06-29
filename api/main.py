# api/main.py

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import time
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
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
    )


# ─── Routes : Observabilité ───────────────────────────────────────────────────

@app.get("/health", tags=["Observability"])
def health_check(db: Session = Depends(get_db)):
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
        page=page,
        page_size=page_size,
    )
    return schemas.IndicatorListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_serialize_indicator(i) for i in items],
    )


@app.get("/indicators/{value:path}", response_model=schemas.IndicatorResponse, tags=["Indicators"])
@limiter.limit("60/minute")
def get_indicator(value: str, request: Request, db: Session = Depends(get_db)):
    """Récupère un indicateur par sa valeur exacte."""
    ind = queries.get_indicator_by_value(db, value)
    if not ind:
        raise HTTPException(status_code=404, detail=f"Indicateur '{value}' introuvable.")
    return _serialize_indicator(ind)


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


# ─── Routes : Stats ───────────────────────────────────────────────────────────

@app.get("/stats", response_model=schemas.StatsResponse, tags=["Stats"])
@limiter.limit("60/minute")
def get_stats(request: Request, db: Session = Depends(get_db)):
    return schemas.StatsResponse(**queries.get_stats(db))