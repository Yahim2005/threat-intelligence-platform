"""add_acronym_to_monitored_assets

Revision ID: a5268afa3b15
Revises: fca0adfc19f5
Create Date: 2026-07-21
"""
from alembic import op

revision = 'a5268afa3b15'
down_revision = 'fca0adfc19f5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE monitored_assets
        ADD COLUMN IF NOT EXISTS acronym VARCHAR(20)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_monitored_assets_acronym
        ON monitored_assets (acronym)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_monitored_assets_acronym")
    op.execute("ALTER TABLE monitored_assets DROP COLUMN IF EXISTS acronym")
