from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.indicator import Indicator

class Enrichment(Base):
    __tablename__ = "enrichments"
    __table_args__ = (
        UniqueConstraint("indicator_id", "provider", name="uq_enrichment_indicator_provider"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    indicator_id: Mapped[UUID] = mapped_column(
        ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[dict | None] = mapped_column(JSONB)
    enriched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="enrichments")