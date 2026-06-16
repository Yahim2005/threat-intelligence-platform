from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.indicator import Indicator

indicator_tags = Table(
    "indicator_tags",
    Base.metadata,
    Column("indicator_id", ForeignKey("indicators.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    indicators: Mapped[list["Indicator"]] = relationship(
        "Indicator", secondary=indicator_tags, back_populates="tags"
    )

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"