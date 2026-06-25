from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import RelationshipType


class TIPRelationship(Base):
    __tablename__ = "relationships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_type: Mapped[RelationshipType] = mapped_column(
        SAEnum(RelationshipType), nullable=False
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    rule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)