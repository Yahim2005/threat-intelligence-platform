"""add_verification_note_to_monitored_assets

Revision ID: 2bbc6a3ffc9f
Revises: 8b86da92ac22
Create Date: 2026-07-24
"""
from alembic import op

revision = '2bbc6a3ffc9f'
down_revision = '8b86da92ac22'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE monitored_assets
        ADD COLUMN IF NOT EXISTS verification_note TEXT
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE monitored_assets DROP COLUMN IF EXISTS verification_note")
