"""
Modèle MonitoredAsset — institutions et infrastructures camerounaises
sous surveillance active (typosquatting, certificate transparency,
surface d'attaque).

Contrairement aux Indicators (menaces externes), ces entités
représentent NOTRE PROPRE périmètre à protéger.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import AssetCategory, DomainStatus


class MonitoredAsset(Base):
    __tablename__ = "monitored_assets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    acronym: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[AssetCategory] = mapped_column(SAEnum(AssetCategory), nullable=False)

    domain: Mapped[str | None] = mapped_column(String(255))
    domain_status: Mapped[DomainStatus] = mapped_column(
        SAEnum(DomainStatus), nullable=False, default=DomainStatus.unconfirmed
    )

    asn: Mapped[int | None] = mapped_column(Integer)
    known_aliases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
