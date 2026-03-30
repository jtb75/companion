"""Add account deactivation and deletion support

Revision ID: 004
Revises: 003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "004"
down_revision = "003"


def upgrade() -> None:
    # User table: deactivation and deletion tracking
    op.add_column("users", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("deletion_scheduled_at", sa.DateTime(timezone=True), nullable=True))

    # DeletionAuditLog: details for audit metadata
    op.add_column("deletion_audit_log", sa.Column("details", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("deletion_audit_log", "details")
    op.drop_column("users", "deletion_scheduled_at")
    op.drop_column("users", "deactivated_at")
