"""Add deletion_settings to config category enum

Revision ID: 007
Revises: 006
"""

from alembic import op

revision = "007"
down_revision = "006"


def upgrade() -> None:
    op.execute("ALTER TYPE configcategory ADD VALUE IF NOT EXISTS 'DELETION_SETTINGS'")


def downgrade() -> None:
    pass
