"""
Modèle ApiClient — organismes externes autorisés à consommer nos exports
et notre serveur TAXII (autre CIRT régional, SIEM/pare-feu partenaire...).

Remplace la TIP_API_KEY unique partagée : chaque organisme a sa propre clé,
révocable indépendamment sans affecter les autres, avec un nom/contact
associé pour l'audit (voir api/auth.py et le log structuré dans api/main.py).

Seul le hash SHA-256 de la clé est stocké — jamais la clé en clair.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiClient(Base):
    __tablename__ = "api_clients"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255))

    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
