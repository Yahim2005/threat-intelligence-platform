"""add cve value to ioctype enum

Revision ID: 234f2df1f8e8
Revises: 5bb939e01820
Create Date: 2026-06-16 11:44:39.942465

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '234f2df1f8e8'
down_revision: Union[str, Sequence[str], None] = '5bb939e01820'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE ioctype ADD VALUE IF NOT EXISTS 'cve'")


def downgrade() -> None:
    # PostgreSQL ne permet pas de retirer une valeur d'un enum facilement.
    # On laisse volontairement le downgrade vide (no-op) — limitation connue de PostgreSQL.
    pass
