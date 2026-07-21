"""add_phone_to_ioctype_enum

Revision ID: 2a86bedeac30
Revises: 0a8337111370
Create Date: 2026-07-20
"""
from alembic import op

revision = '2a86bedeac30'
down_revision = '0a8337111370'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE ioctype ADD VALUE IF NOT EXISTS 'phone'")


def downgrade() -> None:
    pass  # PostgreSQL ne permet pas de supprimer une valeur d'enum
