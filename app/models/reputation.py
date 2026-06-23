from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.indicator import Indicator


class ReputationCache(Base):
    __tablename__ = "reputation_cache"
    __table_args__ = (
        UniqueConstraint(
            "indicator_id",
            "source",
            name="ix_reputation_cache_indicator_source",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    indicator_id: Mapped[UUID] = mapped_column(
        ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(
        Enum("abuseipdb", "virustotal", name="reputationsource", create_type=False),
        nullable=False,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    abuse_confidence_score: Mapped[int | None] = mapped_column(Integer)
    vt_malicious: Mapped[int | None] = mapped_column(Integer)
    vt_total: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)

    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="reputation_cache")  # noqa: F821