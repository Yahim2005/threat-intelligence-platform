# api/taxii.py
"""
Serveur TAXII 2.1 minimal (producteur, lecture seule).

Expose les indicateurs actifs de la plateforme sous forme d'une collection
STIX 2.1 consommable automatiquement par des outils tiers compatibles TAXII
(SIEM, MISP, OpenCTI...), sans intervention manuelle -- contrairement a
l'export STIX ponctuel (/export/stix), un client TAXII peut se brancher une
fois et interroger la collection en continu selon le protocole standard.

Implemente le sous-ensemble du protocole necessaire a un consommateur :
Discovery -> API Root -> Collections -> Objects/Manifest.
Reference : https://docs.oasis-open.org/cti/taxii/v2.1/taxii-v2.1.html
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal
from api.auth import get_api_key
from api.exports import _fetch_exportable
from core.stix import to_stix
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/taxii2", tags=["TAXII"])

TAXII_MEDIA_TYPE = "application/taxii+json;version=2.1"
STIX_MEDIA_TYPE = "application/stix+json;version=2.1"

# UUID fixe pour notre unique collection -- stable dans le temps, ne JAMAIS
# regenerer (les clients TAXII s'appuient sur cet identifiant d'un appel a
# l'autre pour retrouver la meme collection).
COLLECTION_ID = "365fed99-08fa-4fcd-a1b3-fb247eb41d01"
API_ROOT_PATH = "/taxii2/api"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _taxii_response(content: dict, status_code: int = 200):
    return JSONResponse(content=content, media_type=TAXII_MEDIA_TYPE, status_code=status_code)


def _collection_descriptor() -> dict:
    return {
        "id": COLLECTION_ID,
        "title": "Indicateurs actifs",
        "description": "Tous les IOCs actifs de la plateforme (au-dessus d'un seuil de confidence), tous types confondus.",
        "can_read": True,
        "can_write": False,
        "media_types": [STIX_MEDIA_TYPE],
    }


@router.get("/", summary="TAXII Discovery")
def discovery(_key: str = Depends(get_api_key)):
    """Point d'entree TAXII : liste les API roots disponibles."""
    return _taxii_response({
        "title": "TIP ANTIC/CIRT Cameroun",
        "description": "Serveur TAXII 2.1 (lecture seule) exposant les indicateurs actifs de la plateforme.",
        "default": API_ROOT_PATH,
        "api_roots": [API_ROOT_PATH],
    })


@router.get("/api", summary="TAXII API Root")
def api_root(_key: str = Depends(get_api_key)):
    """Decrit les capacites de cet API root."""
    return _taxii_response({
        "title": "TIP - API Root",
        "description": "Indicateurs actifs, exportables en STIX 2.1.",
        "versions": [TAXII_MEDIA_TYPE],
        "max_content_length": 10485760,
    })


@router.get("/api/collections", summary="Lister les collections")
def list_collections(_key: str = Depends(get_api_key)):
    return _taxii_response({"collections": [_collection_descriptor()]})


@router.get("/api/collections/{collection_id}", summary="Detail d'une collection")
def get_collection(collection_id: str, _key: str = Depends(get_api_key)):
    if collection_id != COLLECTION_ID:
        return _taxii_response({"title": "Collection introuvable"}, status_code=404)
    return _taxii_response(_collection_descriptor())


@router.get("/api/collections/{collection_id}/objects", summary="Recuperer les objets STIX")
def get_objects(
    collection_id: str,
    limit: int = Query(500, ge=1, le=2000),
    type: Optional[str] = Query(None, description="Filtrer par type d'objet STIX, ex: indicator"),
    confidence_min: int = Query(50, ge=0, le=100),
    db: Session = Depends(get_db),
    _key: str = Depends(get_api_key),
):
    """Renvoie les objets STIX de la collection, au format attendu par tout
    client TAXII 2.1 (MISP, OpenCTI, SIEM compatibles...). Pagination simple
    par 'limit' -- suffisant pour un volume d'indicateurs actifs raisonnable."""
    if collection_id != COLLECTION_ID:
        return _taxii_response({"title": "Collection introuvable"}, status_code=404)

    # Marge : certains types d'IOC (ex: cve) ne se convertissent pas en objet
    # STIX "indicator" et sont ignores -- on sur-recupere pour compenser et
    # renvoyer bien 'limit' objets valides quand la donnee le permet.
    candidates = _fetch_exportable(db, ioc_type=None, confidence_min=confidence_min)[:limit * 3]
    stix_objects = []
    for ind in candidates:
        if len(stix_objects) >= limit:
            break
        try:
            obj = to_stix(ind)
            if obj:
                stix_objects.append(json.loads(obj.serialize()))
        except Exception:
            continue

    if type:
        stix_objects = [o for o in stix_objects if o.get("type") == type]

    return _taxii_response({"more": len(stix_objects) == limit, "objects": stix_objects})


@router.get("/api/collections/{collection_id}/manifest", summary="Manifeste (metadonnees seules)")
def get_manifest(
    collection_id: str,
    limit: int = Query(500, ge=1, le=2000),
    confidence_min: int = Query(50, ge=0, le=100),
    db: Session = Depends(get_db),
    _key: str = Depends(get_api_key),
):
    """Version allegee de /objects : ne renvoie que les identifiants et
    dates, sans le contenu complet -- utile pour un client qui veut d'abord
    verifier ce qui a change avant de tout retelecharger."""
    if collection_id != COLLECTION_ID:
        return _taxii_response({"title": "Collection introuvable"}, status_code=404)

    candidates = _fetch_exportable(db, ioc_type=None, confidence_min=confidence_min)[:limit * 3]
    manifest_objects = []
    for ind in candidates:
        if len(manifest_objects) >= limit:
            break
        try:
            obj = to_stix(ind)
            if not obj:
                continue
            parsed = json.loads(obj.serialize())
            manifest_objects.append({
                "id": parsed["id"],
                "date_added": parsed.get("created", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")),
                "version": parsed.get("modified", parsed.get("created")),
                "media_type": STIX_MEDIA_TYPE,
            })
        except Exception as e:
            logger.warning(f"[TAXII manifest] Erreur sur un indicateur : {e}")
            continue

    return _taxii_response({"more": len(manifest_objects) == limit, "objects": manifest_objects})
