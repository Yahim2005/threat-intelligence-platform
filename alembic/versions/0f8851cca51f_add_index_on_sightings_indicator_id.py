"""add index on sightings indicator_id

Revision ID: 0f8851cca51f
Revises: 74fe5ca06a47
Create Date: 2026-06-22 09:07:53.381595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f8851cca51f'
down_revision: Union[str, Sequence[str], None] = '74fe5ca06a47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_sighting_indicator_id", "sightings", ["indicator_id"])


def downgrade() -> None:
    op.drop_index("ix_sighting_indicator_id", table_name="sightings")
