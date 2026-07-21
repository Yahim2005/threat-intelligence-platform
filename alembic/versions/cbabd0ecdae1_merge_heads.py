"""merge_heads

Revision ID: cbabd0ecdae1
Revises: 20be681fb9fc, 2a86bedeac30
Create Date: 2026-07-21 08:46:28.294183

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbabd0ecdae1'
down_revision: Union[str, Sequence[str], None] = ('20be681fb9fc', '2a86bedeac30')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
