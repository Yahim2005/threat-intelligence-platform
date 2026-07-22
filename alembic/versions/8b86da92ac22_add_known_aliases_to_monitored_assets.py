"""add_known_aliases_to_monitored_assets

Revision ID: 8b86da92ac22
Revises: f6e9ff4b9579
Create Date: 2026-07-22
"""
from alembic import op

revision = '8b86da92ac22'
down_revision = 'f6e9ff4b9579'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE monitored_assets
        ADD COLUMN IF NOT EXISTS known_aliases JSONB NOT NULL DEFAULT '[]'::jsonb
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE monitored_assets DROP COLUMN IF EXISTS known_aliases")
