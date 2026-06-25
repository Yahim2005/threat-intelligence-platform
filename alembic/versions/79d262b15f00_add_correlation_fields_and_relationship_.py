"""add_correlation_fields_and_relationship_types

Revision ID: 79d262b15f00
Revises: 82b456b4c1e4
Create Date: 2026-06-25 09:08:55.074625
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "79d262b15f00"
down_revision: Union[str, Sequence[str], None] = "82b456b4c1e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ajouter les nouvelles valeurs à l'enum PostgreSQL existant
    op.execute("ALTER TYPE relationshiptype ADD VALUE IF NOT EXISTS 'resolves_to'")
    op.execute("ALTER TYPE relationshiptype ADD VALUE IF NOT EXISTS 'same_source_batch'")
    op.execute("ALTER TYPE relationshiptype ADD VALUE IF NOT EXISTS 'same_tag'")

    # 2. Ajouter confidence et rule à la table relationships
    op.add_column(
        "relationships",
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="50"),
    )
    op.add_column(
        "relationships",
        sa.Column("rule", sa.String(100), nullable=True),
    )

    # 3. Index pour retrouver rapidement les relations d'un indicateur
    op.create_index(
        "ix_relationships_source_ref",
        "relationships",
        ["source_ref"],
    )
    op.create_index(
        "ix_relationships_target_ref",
        "relationships",
        ["target_ref"],
    )


def downgrade() -> None:
    op.drop_index("ix_relationships_target_ref", table_name="relationships")
    op.drop_index("ix_relationships_source_ref", table_name="relationships")
    op.drop_column("relationships", "rule")
    op.drop_column("relationships", "confidence")
    # Note : PostgreSQL ne permet pas de supprimer des valeurs d'un enum
    # Les valeurs resolves_to, same_source_batch, same_tag restent dans le type
