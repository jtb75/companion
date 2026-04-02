"""Add extraction_prompt to configcategory enum.

Revision ID: 012
Revises: 011
"""

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE configcategory ADD VALUE IF NOT EXISTS 'extraction_prompt'")


def downgrade() -> None:
    pass  # Cannot remove enum values in PostgreSQL
