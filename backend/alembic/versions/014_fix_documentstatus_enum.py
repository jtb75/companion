"""Add uppercase PENDING_REVIEW to documentstatus enum.

Revision ID: 014
Revises: 013
"""

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE documentstatus ADD VALUE"
        " IF NOT EXISTS 'PENDING_REVIEW'"
    )


def downgrade() -> None:
    pass
