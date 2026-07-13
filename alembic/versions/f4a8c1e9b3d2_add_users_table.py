"""add users table

Revision ID: f4a8c1e9b3d2
Revises: acbdc71dda29
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f4a8c1e9b3d2"
down_revision = "acbdc71dda29"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Créer le type enum PostgreSQL pour le rôle
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'user')")

    # 2. Créer la table users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "user", name="userrole", create_type=False),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 3. Contraintes d'unicité
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint("uq_users_phone", "users", ["phone"])


def downgrade() -> None:
    op.drop_constraint("uq_users_phone", "users", type_="unique")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_table("users")
    op.execute("DROP TYPE userrole")