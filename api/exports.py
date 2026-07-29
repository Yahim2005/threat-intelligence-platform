# api/exports.py

from __future__ import annotations
import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Indicator
from app.models.api_client import ApiClient
from app.models.enums import IndicatorStatus
from api.auth import get_api_key
from api.rate_limit import client_limiter
from core.stix import to_stix
import stix2
import json

router = APIRouter(prefix="/export", tags=["Exports"])

# 20/minute par organisme (clé API) : ces exports scannent toute la table
# Indicator à chaque appel (voir _fetch_exportable) -- un usage légitime est
# un cron horaire/quotidien, pas un polling serré. Rate limit par identité de
# clé API (pas par IP) : voir api/rate_limit.py.


# ─── Dépendance DB ───────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Requête commune aux trois exports ───────────────────────────────────────

def _exportable_base_query(
    session: Session,
    ioc_type: Optional[str],
    confidence_min: int,
):
    """
    Query (non exécutée) des indicateurs exportables, sans tri :
    - statut active (jamais whitelisted ni expired)
    - confidence >= seuil
    - filtrables par type
    Factorisée pour être réutilisable par des consommateurs qui ont besoin
    de leur propre tri/curseur (voir api/taxii.py pour la pagination TAXII).
    """
    q = (
        session.query(Indicator)
        .filter(Indicator.status == IndicatorStatus.active)
        .filter(Indicator.confidence >= confidence_min)
    )
    if ioc_type:
        q = q.filter(Indicator.type == ioc_type)
    else:
        # Les CVE ne sont pas convertibles en objet STIX "indicator" (to_stix
        # les rejette) : les exclure par defaut evite qu'un lot volumineux et
        # regroupe physiquement en base (ex: import NVD massif) ne remonte en
        # bloc et masque silencieusement tous les autres types au tri.
        q = q.filter(Indicator.type != "cve")
    return q


def _fetch_exportable(
    session: Session,
    ioc_type: Optional[str],
    confidence_min: int,
) -> list[Indicator]:
    """Version triée-et-exécutée de _exportable_base_query, utilisée par les
    exports ponctuels (/export/*) qui veulent les indicateurs les plus fiables
    en premier."""
    # Tri secondaire stable : sans lui, des lignes a confidence identique
    # (cas courant, la plupart des collecteurs assignent 50 par defaut)
    # peuvent ressortir regroupees par bloc d'insertion plutot que melangees.
    return (
        _exportable_base_query(session, ioc_type, confidence_min)
        .order_by(Indicator.confidence.desc(), Indicator.created_at.desc())
        .all()
    )


# ─── Export STIX 2.1 ─────────────────────────────────────────────────────────

@router.get("/stix", summary="Exporter un bundle STIX 2.1")
@client_limiter.limit("20/minute")
def export_stix(
    request: Request,
    type: Optional[str] = Query(None, description="Filtrer par type d'IOC"),
    confidence_min: int = Query(50, ge=0, le=100, description="Confidence minimum"),
    db: Session = Depends(get_db),
    _client: ApiClient | None = Depends(get_api_key),
):
    """
    Retourne un bundle STIX 2.1 contenant les indicateurs actifs
    au-dessus du seuil de confidence.
    Protégé par clé API (header X-API-Key).
    """
    indicators = _fetch_exportable(db, ioc_type=type, confidence_min=confidence_min)

    stix_objects = []
    for ind in indicators:
        try:
            obj = to_stix(ind)
            if obj:
                stix_objects.append(obj)
        except Exception:
            continue

    bundle = stix2.Bundle(objects=stix_objects, allow_custom=True)

    # nouveau
    import json
    return JSONResponse(
        content=json.loads(bundle.serialize(pretty=False, ensure_ascii=False)),
        media_type="application/stix+json",
    )


# ─── Export CSV ──────────────────────────────────────────────────────────────

@router.get("/csv", summary="Exporter les indicateurs en CSV")
@client_limiter.limit("20/minute")
def export_csv(
    request: Request,
    type: Optional[str] = Query(None, description="Filtrer par type d'IOC"),
    confidence_min: int = Query(50, ge=0, le=100, description="Confidence minimum"),
    db: Session = Depends(get_db),
    _client: ApiClient | None = Depends(get_api_key),
):
    """
    Retourne un fichier CSV téléchargeable avec les indicateurs actifs.
    Protégé par clé API (header X-API-Key).
    """
    indicators = _fetch_exportable(db, ioc_type=type, confidence_min=confidence_min)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "value", "type", "confidence", "tlp",
        "first_seen", "last_seen", "source", "tags"
    ])

    for ind in indicators:
        writer.writerow([
            ind.value,
            ind.type.value if hasattr(ind.type, "value") else str(ind.type),
            ind.confidence,
            ind.tlp.value if hasattr(ind.tlp, "value") else str(ind.tlp),
            ind.first_seen.isoformat() if ind.first_seen else "",
            ind.last_seen.isoformat() if ind.last_seen else "",
            ind.source.name if ind.source else "",
            "|".join(t.name for t in ind.tags) if ind.tags else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tip_export.csv"},
    )


# ─── Export Blocklist ────────────────────────────────────────────────────────

@router.get("/blocklist", summary="Exporter une blocklist opérationnelle")
@client_limiter.limit("20/minute")
def export_blocklist(
    request: Request,
    type: Optional[str] = Query(None, description="Filtrer par type : ip, domain, url"),
    confidence_min: int = Query(70, ge=0, le=100, description="Confidence minimum (défaut 70)"),
    db: Session = Depends(get_db),
    _client: ApiClient | None = Depends(get_api_key),
):
    """
    Retourne une liste brute de valeurs (une par ligne) pour import
    direct dans un firewall ou DNS RPZ.
    Seuil par défaut 70 car usage opérationnel direct.
    Protégé par clé API (header X-API-Key).
    """
    indicators = _fetch_exportable(db, ioc_type=type, confidence_min=confidence_min)

    lines = [ind.value for ind in indicators]
    content = "\n".join(lines) + "\n" if lines else "\n"

    return StreamingResponse(
        iter([content]),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=tip_blocklist.txt"},
    )