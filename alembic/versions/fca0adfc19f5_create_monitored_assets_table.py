"""create_monitored_assets_table

Revision ID: fca0adfc19f5
Revises: cbabd0ecdae1
Create Date: 2026-07-21
"""
from alembic import op

revision = 'fca0adfc19f5'
down_revision = 'cbabd0ecdae1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE assetcategory AS ENUM (
            'telecom', 'ministry', 'bank', 'public_company', 'institution'
        )
    """)
    op.execute("""
        CREATE TYPE domainstatus AS ENUM (
            'confirmed', 'unconfirmed', 'not_found'
        )
    """)
    op.execute("""
        CREATE TABLE monitored_assets (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category assetcategory NOT NULL,
            domain VARCHAR(255),
            domain_status domainstatus NOT NULL DEFAULT 'unconfirmed',
            asn INTEGER,
            active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX ix_monitored_assets_domain ON monitored_assets (domain)
    """)
    op.execute("""
        CREATE INDEX ix_monitored_assets_category ON monitored_assets (category)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS monitored_assets")
    op.execute("DROP TYPE IF EXISTS assetcategory")
    op.execute("DROP TYPE IF EXISTS domainstatus")
