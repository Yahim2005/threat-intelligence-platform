"""add_reputation_cache

Revision ID: 82b456b4c1e4
Revises: 0f8851cca51f
Create Date: 2026-06-23 09:25:44.269481
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "82b456b4c1e4"
down_revision: Union[str, Sequence[str], None] = "0f8851cca51f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE reputationsource AS ENUM ('abuseipdb', 'virustotal')"
    )

    op.create_table(
        "reputation_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("raw_response", postgresql.JSONB(), nullable=True),
        sa.Column("abuse_confidence_score", sa.Integer(), nullable=True),
        sa.Column("vt_malicious", sa.Integer(), nullable=True),
        sa.Column("vt_total", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["indicator_id"],
            ["indicators.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Convertir la colonne source en type PostgreSQL natif reputationsource
    op.execute(
        "ALTER TABLE reputation_cache "
        "ALTER COLUMN source TYPE reputationsource "
        "USING source::reputationsource"
    )

    op.create_index(
        "ix_reputation_cache_indicator_id",
        "reputation_cache",
        ["indicator_id"],
    )

    op.create_index(
        "ix_reputation_cache_indicator_source",
        "reputation_cache",
        ["indicator_id", "source"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_reputation_cache_indicator_source", table_name="reputation_cache")
    op.drop_index("ix_reputation_cache_indicator_id", table_name="reputation_cache")
    op.drop_table("reputation_cache")
    op.execute("DROP TYPE IF EXISTS reputationsource")