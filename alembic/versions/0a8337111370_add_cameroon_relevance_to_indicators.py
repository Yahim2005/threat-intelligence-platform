"""add_cameroon_relevance_to_indicators

Revision ID: 0a8337111370
Revises: f4a8c1e9b3d2
Create Date: 2026-07-20
"""
from alembic import op

revision = '0a8337111370'
down_revision = 'f4a8c1e9b3d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE indicators
        ADD COLUMN IF NOT EXISTS cameroon_relevance INTEGER NOT NULL DEFAULT 0
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_indicators_cameroon_relevance
        ON indicators (cameroon_relevance)
        WHERE cameroon_relevance > 0
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_indicators_cameroon_relevance")
    op.execute("ALTER TABLE indicators DROP COLUMN IF EXISTS cameroon_relevance")
