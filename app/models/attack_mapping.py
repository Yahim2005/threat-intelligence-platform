from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.indicator import Indicator

class AttackMapping(Base):
    __tablename__ = "attack_mappings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    indicator_id: Mapped[UUID] = mapped_column(
        ForeignKey("indicators.id", ondelete="CASCADE"), nullable=False
    )
    technique_id: Mapped[str] = mapped_column(String(20), nullable=False)  # ex: T1566
    tactic: Mapped[str | None] = mapped_column(String(100))  # ex: initial-access
    confidence: Mapped[int] = mapped_column(Integer, default=50)

    indicator: Mapped["Indicator"] = relationship("Indicator", back_populates="attack_mappings")