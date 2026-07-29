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

Pagination (section 5.3 du spec) : added_after (filtre incrémental) + next
(curseur opaque renvoyé dans la réponse, à repasser tel quel à l'appel
suivant). Remplace l'ancien "limit" seul -- voir docs/taxii_integration.md
pour un exemple de boucle de synchronisation cote client.
"""
from __future__ import annotations
import base64
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import tuple_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Indicator
from app.models.api_client import ApiClient
from api.auth import get_api_key
from api.exports import _exportable_base_query
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


# ─── Pagination par curseur ───────────────────────────────────────────────────
# Curseur opaque = base64("<created_at ISO>|<id>") du dernier Indicator brut
# examiné (avant conversion STIX). Ancré sur les lignes brutes plutôt que sur
# les objets STIX convertis avec succès : ainsi le curseur avance toujours
# de façon cohérente même quand certaines lignes (ex: type "cve", non
# convertible) sont ignorées, sans jamais sauter ni rejouer un IOC.

def _encode_cursor(created_at: datetime, ind_id) -> str:
    raw = f"{created_at.isoformat()}|{ind_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_str, id_str = raw.rsplit("|", 1)
        return datetime.fromisoformat(ts_str), UUID(id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Paramètre 'next' invalide ou expiré.")


def _parse_added_after(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Paramètre 'added_after' invalide : attendu au format ISO 8601 (ex: 2026-01-01T00:00:00Z).",
        )
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _paginated_indicators(
    db: Session,
    confidence_min: int,
    added_after: Optional[str],
    next_cursor: Optional[str],
    limit: int,
) -> tuple[list[Indicator], bool]:
    """
    Renvoie jusqu'à `limit` indicateurs bruts (+ indicateur `more`), triés de
    façon stable par (created_at, id) croissant -- l'ordre choisi pour que la
    pagination par curseur avance de façon monotone, adapté à une synchro
    incrémentale (contrairement au tri par confidence des exports ponctuels).
    """
    q = _exportable_base_query(db, ioc_type=None, confidence_min=confidence_min)

    if added_after:
        q = q.filter(Indicator.created_at > _parse_added_after(added_after))

    if next_cursor:
        cursor_dt, cursor_id = _decode_cursor(next_cursor)
        q = q.filter(tuple_(Indicator.created_at, Indicator.id) > (cursor_dt, cursor_id))

    rows = (
        q.order_by(Indicator.created_at.asc(), Indicator.id.asc())
        .limit(limit + 1)
        .all()
    )
    more = len(rows) > limit
    return rows[:limit], more


@router.get("/", summary="TAXII Discovery")
def discovery(_client: ApiClient | None = Depends(get_api_key)):
    """Point d'entree TAXII : liste les API roots disponibles."""
    return _taxii_response({
        "title": "TIP ANTIC/CIRT Cameroun",
        "description": "Serveur TAXII 2.1 (lecture seule) exposant les indicateurs actifs de la plateforme.",
        "default": API_ROOT_PATH,
        "api_roots": [API_ROOT_PATH],
    })


@router.get("/api", summary="TAXII API Root")
def api_root(_client: ApiClient | None = Depends(get_api_key)):
    """Decrit les capacites de cet API root."""
    return _taxii_response({
        "title": "TIP - API Root",
        "description": "Indicateurs actifs, exportables en STIX 2.1.",
        "versions": [TAXII_MEDIA_TYPE],
        "max_content_length": 10485760,
    })


@router.get("/api/collections", summary="Lister les collections")
def list_collections(_client: ApiClient | None = Depends(get_api_key)):
    return _taxii_response({"collections": [_collection_descriptor()]})


@router.get("/api/collections/{collection_id}", summary="Detail d'une collection")
def get_collection(collection_id: str, _client: ApiClient | None = Depends(get_api_key)):
    if collection_id != COLLECTION_ID:
        return _taxii_response({"title": "Collection introuvable"}, status_code=404)
    return _taxii_response(_collection_descriptor())


@router.get("/api/collections/{collection_id}/objects", summary="Recuperer les objets STIX")
def get_objects(
    collection_id: str,
    limit: int = Query(500, ge=1, le=2000),
    type: Optional[str] = Query(None, description="Filtrer par type d'objet STIX, ex: indicator"),
    confidence_min: int = Query(50, ge=0, le=100),
    added_after: Optional[str] = Query(None, description="ISO 8601 -- ne renvoyer que les IOCs créés après cette date"),
    next: Optional[str] = Query(None, description="Curseur opaque renvoyé par la réponse précédente"),
    db: Session = Depends(get_db),
    _client: ApiClient | None = Depends(get_api_key),
):
    """Renvoie les objets STIX de la collection, au format attendu par tout
    client TAXII 2.1 (MISP, OpenCTI, SIEM compatibles...).

    Pagination conforme au spec (section 5.3) : `added_after` filtre les IOCs
    créés après une date donnée, `next` reprend une pagination en cours. Une
    page peut contenir moins de `limit` objets si certaines lignes de la
    fenêtre ne se convertissent pas en STIX (ex: type "cve") -- ce n'est pas
    une anomalie, `more`/`next` restent fiables pour poursuivre la synchro.
    """
    if collection_id != COLLECTION_ID:
        return _taxii_response({"title": "Collection introuvable"}, status_code=404)

    rows, more = _paginated_indicators(db, confidence_min, added_after, next, limit)

    stix_objects = []
    for ind in rows:
        try:
            obj = to_stix(ind)
            if obj:
                stix_objects.append(json.loads(obj.serialize()))
        except Exception:
            continue

    if type:
        stix_objects = [o for o in stix_objects if o.get("type") == type]

    response = {"more": more, "objects": stix_objects}
    if more and rows:
        response["next"] = _encode_cursor(rows[-1].created_at, rows[-1].id)
    return _taxii_response(response)


@router.get("/api/collections/{collection_id}/manifest", summary="Manifeste (metadonnees seules)")
def get_manifest(
    collection_id: str,
    limit: int = Query(500, ge=1, le=2000),
    confidence_min: int = Query(50, ge=0, le=100),
    added_after: Optional[str] = Query(None, description="ISO 8601 -- ne renvoyer que les IOCs créés après cette date"),
    next: Optional[str] = Query(None, description="Curseur opaque renvoyé par la réponse précédente"),
    db: Session = Depends(get_db),
    _client: ApiClient | None = Depends(get_api_key),
):
    """Version allegee de /objects : ne renvoie que les identifiants et
    dates, sans le contenu complet -- utile pour un client qui veut d'abord
    verifier ce qui a change avant de tout retelecharger. Meme mecanique de
    pagination que /objects (added_after + next)."""
    if collection_id != COLLECTION_ID:
        return _taxii_response({"title": "Collection introuvable"}, status_code=404)

    rows, more = _paginated_indicators(db, confidence_min, added_after, next, limit)

    manifest_objects = []
    for ind in rows:
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

    response = {"more": more, "objects": manifest_objects}
    if more and rows:
        response["next"] = _encode_cursor(rows[-1].created_at, rows[-1].id)
    return _taxii_response(response)
