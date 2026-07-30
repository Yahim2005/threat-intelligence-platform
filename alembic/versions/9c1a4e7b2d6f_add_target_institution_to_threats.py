"""add_target_institution_to_threats

Revision ID: 9c1a4e7b2d6f
Revises: 0c7f9f2b9b99
Create Date: 2026-07-29
"""
from alembic import op

revision = '9c1a4e7b2d6f'
down_revision = '0c7f9f2b9b99'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE threats
        ADD COLUMN IF NOT EXISTS target_institution_id UUID
        REFERENCES monitored_assets(id) ON DELETE SET NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_threats_target_institution_id
        ON threats (target_institution_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_threats_target_institution_id")
    op.execute("ALTER TABLE threats DROP COLUMN IF EXISTS target_institution_id")
