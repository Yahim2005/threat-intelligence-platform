"""create_admin_job_runs_table

Revision ID: d4f8b2a1c9e3
Revises: b3e7f19a6c2d
Create Date: 2026-07-31
"""
from alembic import op

revision = 'd4f8b2a1c9e3'
down_revision = 'b3e7f19a6c2d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE admin_job_runs (
            id UUID PRIMARY KEY,
            job_name VARCHAR(100) NOT NULL,
            started_at TIMESTAMP NOT NULL DEFAULT now(),
            finished_at TIMESTAMP,
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            exit_code INTEGER,
            detail TEXT
        )
    """)
    op.execute("""
        CREATE INDEX ix_admin_job_runs_job_name_started_at
        ON admin_job_runs (job_name, started_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_admin_job_runs_job_name_started_at")
    op.execute("DROP TABLE IF EXISTS admin_job_runs")
