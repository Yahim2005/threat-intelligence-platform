"""add whitelisted and expired values to indicatorstatus enum

Revision ID: 74fe5ca06a47
Revises: 441e2b55ae8c
Create Date: 2026-06-19 09:27:04.867333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74fe5ca06a47'
down_revision: Union[str, Sequence[str], None] = '441e2b55ae8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE indicatorstatus ADD VALUE IF NOT EXISTS 'whitelisted'")
    op.execute("ALTER TYPE indicatorstatus ADD VALUE IF NOT EXISTS 'expired'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL ne permet pas de retirer une valeur d'un enum facilement.
    pass
