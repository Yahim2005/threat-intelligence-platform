"""
Gestion des destinataires du digest IOC Cameroun depuis le dashboard admin
(voir scripts/send_email_digest.py) -- même pattern que
api/api_clients_routes.py : géré depuis l'admin, pas en dur dans le code.

Toutes les routes sont réservées aux admins (même dépendance require_admin
que /admin/api-clients).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import schemas
from api.auth import get_db, require_admin
from app.models.email_recipient import EmailRecipient
from app.models.user import User

router = APIRouter(prefix="/admin/email-recipients", tags=["Admin"])


def _to_response(recipient: EmailRecipient) -> schemas.EmailRecipientResponse:
    return schemas.EmailRecipientResponse(
        id=str(recipient.id),
        name=recipient.name,
        email=recipient.email,
        is_active=recipient.is_active,
        created_at=recipient.created_at,
    )


@router.get("", response_model=list[schemas.EmailRecipientResponse])
def list_email_recipients(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    recipients = db.query(EmailRecipient).order_by(EmailRecipient.created_at.desc()).all()
    return [_to_response(r) for r in recipients]


@router.post("", response_model=schemas.EmailRecipientResponse)
def create_email_recipient(
    body: schemas.EmailRecipientCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    name = body.name.strip()
    email = body.email.strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="Le nom du destinataire est obligatoire.")
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Adresse email invalide.")

    existing = db.query(EmailRecipient).filter(EmailRecipient.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Cette adresse email est déjà enregistrée.")

    recipient = EmailRecipient(name=name, email=email)
    db.add(recipient)
    db.commit()
    db.refresh(recipient)
    return _to_response(recipient)


@router.post("/{recipient_id}/revoke", response_model=schemas.EmailRecipientResponse)
def revoke_email_recipient(
    recipient_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    recipient = db.query(EmailRecipient).filter(EmailRecipient.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Destinataire introuvable.")

    recipient.is_active = False
    db.commit()
    db.refresh(recipient)
    return _to_response(recipient)
