"""create_exposed_assets_table

Revision ID: f6e9ff4b9579
Revises: a5268afa3b15
Create Date: 2026-07-22
"""
from alembic import op

revision = 'f6e9ff4b9579'
down_revision = 'a5268afa3b15'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE exposed_assets (
            id UUID PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL,
            monitored_asset_id UUID REFERENCES monitored_assets(id) ON DELETE SET NULL,
            hostnames JSONB,
            ports JSONB,
            cpes JSONB,
            vulns JSONB,
            tags JSONB,
            risk_level VARCHAR(20) NOT NULL DEFAULT 'info',
            first_seen TIMESTAMP NOT NULL DEFAULT now(),
            last_seen TIMESTAMP NOT NULL DEFAULT now(),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_exposed_assets_ip ON exposed_assets (ip_address)
    """)
    op.execute("""
        CREATE INDEX ix_exposed_assets_asset ON exposed_assets (monitored_asset_id)
    """)
    op.execute("""
        CREATE INDEX ix_exposed_assets_risk ON exposed_assets (risk_level)
    """)

    # Table de suivi de progression du scan (pour reprise après interruption)
    op.execute("""
        CREATE TABLE exposed_assets_scan_progress (
            id UUID PRIMARY KEY,
            asn INTEGER NOT NULL,
            prefix VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            scanned_at TIMESTAMP,
            UNIQUE (asn, prefix)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS exposed_assets_scan_progress")
    op.execute("DROP TABLE IF EXISTS exposed_assets")
