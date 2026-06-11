from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import TLPLevel, ThreatType


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