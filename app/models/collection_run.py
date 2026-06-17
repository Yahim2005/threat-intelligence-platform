from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RunStatus

if TYPE_CHECKING:
    from app.models.source import Source


class CollectionRun(Base):
    """Journal d'exécution d'un collecteur — un enregistrement par run.
    Base de l'observabilité : permet de voir l'historique sans fouiller les logs.
    """

    __tablename__ = "collection_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus), nullable=False, default=RunStatus.running
    )
    items_created: Mapped[int] = mapped_column(Integer, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, default=0)
    items_errors: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(2048))

    source: Mapped["Source"] = relationship("Source", back_populates="collection_runs")

    def __repr__(self) -> str:
        return f"<CollectionRun {self.source_id} {self.status}>"