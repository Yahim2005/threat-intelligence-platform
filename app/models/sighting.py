from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.indicator import Indicator


class Sighting(Base):
    __tablename__ = "sightings"
    __table_args__ = (
        Index("ix_sighting_seen_at", "seen_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    indicator_id: Mapped[UUID] = mapped_column(
        ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False
    )
    seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(255))
    context: Mapped[dict | None] = mapped_column(JSONB)

    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="sightings")