"""
Modèles pour la surveillance de la surface d'attaque nationale.

ExposedAsset       : une IP camerounaise avec des services/vulnérabilités
                      exposés, détectés via Shodan InternetDB.
ExposedAssetScanProgress : suivi de progression du scan (reprise après
                      interruption — le scan complet peut prendre ~2h).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExposedAsset(Base):
    __tablename__ = "exposed_assets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, unique=True)
    monitored_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("monitored_assets.id", ondelete="SET NULL")
    )

    hostnames: Mapped[list | None] = mapped_column(JSONB)
    ports: Mapped[list | None] = mapped_column(JSONB)
    cpes: Mapped[list | None] = mapped_column(JSONB)
    vulns: Mapped[list | None] = mapped_column(JSONB)
    tags: Mapped[list | None] = mapped_column(JSONB)

    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="info")

    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ExposedAssetScanProgress(Base):
    __tablename__ = "exposed_assets_scan_progress"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    asn: Mapped[int] = mapped_column(nullable=False)
    prefix: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime)
