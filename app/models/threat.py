from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TLPLevel, ThreatType

if TYPE_CHECKING:
    from app.models.indicator import Indicator

# Table de jointure many-to-many déclarée explicitement
threat_indicators = Table(
    "threat_indicators",
    Base.metadata,
    Column("threat_id", PGUUID(as_uuid=True), ForeignKey("threats.id", ondelete="CASCADE"), primary_key=True),
    Column("indicator_id", PGUUID(as_uuid=True), ForeignKey("indicators.id", ondelete="CASCADE"), primary_key=True),
)


class Threat(Base):
    __tablename__ = "threats"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    threat_type: Mapped[ThreatType] = mapped_column(SAEnum(ThreatType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[dict | None] = mapped_column(JSONB)
    tlp: Mapped[TLPLevel] = mapped_column(
        SAEnum(TLPLevel), nullable=False, default=TLPLevel.CLEAR
    )
    stix_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    indicators: Mapped[list["Indicator"]] = relationship(
        "Indicator",
        secondary=threat_indicators,
        back_populates="threats",
    )