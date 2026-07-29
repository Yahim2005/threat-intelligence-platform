"""create_api_clients_table

Revision ID: 0c7f9f2b9b99
Revises: 2bbc6a3ffc9f
Create Date: 2026-07-29
"""
from alembic import op

revision = '0c7f9f2b9b99'
down_revision = '2bbc6a3ffc9f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE api_clients (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            contact_email VARCHAR(255),
            key_hash VARCHAR(64) NOT NULL,
            key_prefix VARCHAR(16) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            last_used_at TIMESTAMP
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_api_clients_key_hash ON api_clients (key_hash)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS api_clients")
