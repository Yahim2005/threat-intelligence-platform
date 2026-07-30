"""create_email_digest_tables

Revision ID: b3e7f19a6c2d
Revises: 9c1a4e7b2d6f
Create Date: 2026-07-30
"""
from alembic import op

revision = 'b3e7f19a6c2d'
down_revision = '9c1a4e7b2d6f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE email_recipients (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_email_recipients_email ON email_recipients (email)
    """)

    op.execute("""
        CREATE TABLE email_digest_log (
            id UUID PRIMARY KEY,
            sent_at TIMESTAMP NOT NULL DEFAULT now(),
            recipient_count INTEGER NOT NULL,
            ioc_count INTEGER NOT NULL
        )
    """)
    op.execute("""
        CREATE INDEX ix_email_digest_log_sent_at ON email_digest_log (sent_at)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS email_digest_log")
    op.execute("DROP INDEX IF EXISTS ix_email_recipients_email")
    op.execute("DROP TABLE IF EXISTS email_recipients")
