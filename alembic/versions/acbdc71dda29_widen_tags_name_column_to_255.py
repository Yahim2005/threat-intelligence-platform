"""widen tags name column to 255

Revision ID: acbdc71dda29
Revises: 1d2d3a495467
Create Date: 2026-06-30 10:53:36.493824

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acbdc71dda29'
down_revision: Union[str, Sequence[str], None] = '1d2d3a495467'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE tags ALTER COLUMN name TYPE VARCHAR(255)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE tags ALTER COLUMN name TYPE VARCHAR(50)")
