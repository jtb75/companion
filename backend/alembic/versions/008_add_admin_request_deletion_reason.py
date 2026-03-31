"""Add admin_request to deletionreason enum

Revision ID: 008
Revises: 007
"""

from alembic import op

revision = "008"
down_revision = "007"


def upgrade() -> None:
    op.execute("ALTER TYPE deletionreason ADD VALUE IF NOT EXISTS 'ADMIN_REQUEST'")


def downgrade() -> None:
    pass
