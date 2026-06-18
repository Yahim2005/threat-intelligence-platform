"""add ipv6 and asn values to ioctype enum

Revision ID: 441e2b55ae8c
Revises: a2bf7e7e8fdb
Create Date: 2026-06-18 09:58:31.045935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '441e2b55ae8c'
down_revision: Union[str, Sequence[str], None] = 'a2bf7e7e8fdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE ioctype ADD VALUE IF NOT EXISTS 'ipv6'")
    op.execute("ALTER TYPE ioctype ADD VALUE IF NOT EXISTS 'asn'")


def downgrade() -> None:
    # PostgreSQL ne permet pas de retirer une valeur d'un enum facilement.
    pass
