"""
Modèle EmailDigestLog — historique des envois réussis du digest IOC
Cameroun. Une ligne n'est insérée que lors d'un envoi réel (jamais en
--dry-run) : sent_at sert de filigrane pour ne jamais renvoyer deux fois
le même IOC (voir core/email_digest.py, first_seen > dernier sent_at) et
pour décider si >= 3 jours se sont écoulés depuis le dernier envoi.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmailDigestLog(Base):
    __tablename__ = "email_digest_log"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ioc_count: Mapped[int] = mapped_column(Integer, nullable=False)
