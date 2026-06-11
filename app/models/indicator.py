from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import IOCType, IndicatorStatus, TLPLevel

if TYPE_CHECKING:
    from app.models.source import Source
    from app.models.sighting import Sighting
    from app.models.enrichment import Enrichment
    from app.models.attack_mapping import AttackMapping

class Indicator(Base):
    __tablename__ = "indicators"
    __table_args__ = (
        UniqueConstraint("value", "type", name="uq_indicator_value_type"),
        Index("ix_indicator_value", "value"),
        Index("ix_indicator_type", "type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    type: Mapped[IOCType] = mapped_column(SAEnum(IOCType), nullable=False)
    tlp: Mapped[TLPLevel] = mapped_column(
        SAEnum(TLPLevel), nullable=False, default=TLPLevel.CLEAR
    )
    confidence: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    status: Mapped[IndicatorStatus] = mapped_column(
        SAEnum(IndicatorStatus), nullable=False, default=IndicatorStatus.active
    )
    first_seen: Mapped[datetime | None] = mapped_column(DateTime)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)
    tags: Mapped[dict | None] = mapped_column(JSONB)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relations (on les utilisera plus tard pour faire des JOIN facilement)
    source: Mapped["Source"] = relationship("Source", back_populates="indicators")
    sightings: Mapped[list["Sighting"]] = relationship(
        "Sighting", back_populates="indicator", cascade="all, delete-orphan"
    )
    enrichments: Mapped[list["Enrichment"]] = relationship(
        "Enrichment", back_populates="indicator", cascade="all, delete-orphan"
    )
    attack_mappings: Mapped[list["AttackMapping"]] = relationship(
        "AttackMapping", back_populates="indicator", cascade="all, delete-orphan"
    )