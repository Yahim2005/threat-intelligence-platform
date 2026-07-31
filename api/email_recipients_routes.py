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
from app.admin_job_runner import launch_tracked_job
from app.models.email_recipient import EmailRecipient
from app.models.user import User
from core.email_digest import get_digest_indicators, get_last_successful_sent_at

router = APIRouter(prefix="/admin/email-recipients", tags=["Admin"])
digest_router = APIRouter(prefix="/admin/email-digest", tags=["Admin"])


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


@digest_router.get("/status", response_model=schemas.EmailDigestStatusResponse)
def email_digest_status(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Compte d'IOCs actuellement éligibles pour le prochain digest -- même
    logique de filtrage que core/email_digest.py (cameroon_relevance >= seuil,
    first_seen postérieur au dernier envoi réussi, plafonné à
    EMAIL_DIGEST_MAX_IOCS), et date du dernier envoi réussi."""
    last_sent = get_last_successful_sent_at(db)
    eligible = get_digest_indicators(db)
    return schemas.EmailDigestStatusResponse(
        eligible_count=len(eligible),
        last_sent_at=last_sent,
    )


@digest_router.post("/send-now")
def send_digest_now(
    _admin: User = Depends(require_admin),
):
    """Déclenche un envoi immédiat du digest (équivalent de
    scripts/send_email_digest.py --force), sans attendre le cycle
    automatique de 3 jours. Même mécanisme de suivi en arrière-plan que les
    autres jobs admin (voir app/admin_job_runner.py)."""
    launch_tracked_job("email_digest_send_now", ["python", "-m", "scripts.send_email_digest", "--force"])
    return {"message": "Envoi du digest lancé en arrière-plan."}
