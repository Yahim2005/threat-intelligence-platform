"""add_threat_indicators_junction

Revision ID: 1d2d3a495467
Revises: 79d262b15f00
Create Date: 2026-06-25 09:46:37.585061
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1d2d3a495467"
down_revision: Union[str, Sequence[str], None] = "79d262b15f00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table de jointure many-to-many entre threats et indicators
    op.create_table(
        "threat_indicators",
        sa.Column("threat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["threat_id"], ["threats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["indicator_id"], ["indicators.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("threat_id", "indicator_id"),
    )
    op.create_index(
        "ix_threat_indicators_threat_id",
        "threat_indicators",
        ["threat_id"],
    )
    op.create_index(
        "ix_threat_indicators_indicator_id",
        "threat_indicators",
        ["indicator_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_threat_indicators_indicator_id", table_name="threat_indicators")
    op.drop_index("ix_threat_indicators_threat_id", table_name="threat_indicators")
    op.drop_table("threat_indicators")