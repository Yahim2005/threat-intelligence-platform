"""add_phone_to_ioctype_enum

Revision ID: 20be681fb9fc
Revises: 0a8337111370
Create Date: 2026-07-21 08:44:35.752391

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20be681fb9fc'
down_revision: Union[str, Sequence[str], None] = '0a8337111370'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
