from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import SourceType, TLPLevel

if TYPE_CHECKING:
    from app.models.indicator import Indicator

class Source(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType), nullable=False, default=SourceType.feed
    )
    tlp: Mapped[TLPLevel] = mapped_column(
        SAEnum(TLPLevel), nullable=False, default=TLPLevel.CLEAR
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    from sqlalchemy.orm import relationship
    indicators: Mapped[list["Indicator"]] = relationship(
        "Indicator", back_populates="source"
    )
    