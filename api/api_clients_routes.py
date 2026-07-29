# api/api_clients_routes.py
"""
Gestion des clients API (organismes partenaires) depuis le dashboard admin --
équivalent web de scripts/manage_api_keys.py, mêmes garanties :
- la clé en clair n'est jamais stockée, ni relue après sa création
- révocation immédiate (is_active=False), effective dès la requête suivante
  sur toute route protégée par X-API-Key (voir api/auth.py, get_api_key)

Toutes les routes sont réservées aux admins (même dépendance que
/admin/jobs dans api/main.py).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import schemas
from api.auth import get_db, require_admin
from app.api_clients import create_api_client
from app.models.api_client import ApiClient
from app.models.user import User

router = APIRouter(prefix="/admin/api-clients", tags=["Admin"])


def _to_response(client: ApiClient) -> schemas.ApiClientResponse:
    return schemas.ApiClientResponse(
        id=str(client.id),
        name=client.name,
        contact_email=client.contact_email,
        is_active=client.is_active,
        created_at=client.created_at,
        last_used_at=client.last_used_at,
    )


@router.get("", response_model=list[schemas.ApiClientResponse])
def list_api_clients(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Liste tous les clients API. Ne renvoie jamais le hash ni la clé."""
    clients = db.query(ApiClient).order_by(ApiClient.created_at.desc()).all()
    return [_to_response(c) for c in clients]


@router.post("", response_model=schemas.ApiClientCreateResponse)
def create_api_client_route(
    body: schemas.ApiClientCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Crée un nouveau client API et renvoie la clé en clair -- UNE SEULE
    FOIS, dans cette réponse. Elle ne sera plus jamais exposée ensuite,
    y compris via GET /admin/api-clients."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom de l'organisme est obligatoire.")

    client, raw_key = create_api_client(db, name=name, contact_email=body.contact_email)
    return schemas.ApiClientCreateResponse(
        id=str(client.id),
        name=client.name,
        contact_email=client.contact_email,
        is_active=client.is_active,
        created_at=client.created_at,
        last_used_at=client.last_used_at,
        api_key=raw_key,
    )


@router.post("/{client_id}/revoke", response_model=schemas.ApiClientResponse)
def revoke_api_client(
    client_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Révoque une clé -- effet immédiat, irréversible sans en recréer une."""
    client = db.query(ApiClient).filter(ApiClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client API introuvable.")

    client.is_active = False
    db.commit()
    db.refresh(client)
    return _to_response(client)
