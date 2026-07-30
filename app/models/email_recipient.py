"""
Modèle EmailRecipient — destinataires du digest IOC Cameroun envoyé
périodiquement (voir scripts/send_email_digest.py). Gérés depuis le
dashboard Admin, pas en dur dans le code (même pattern que ApiClient).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmailRecipient(Base):
    __tablename__ = "email_recipients"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
