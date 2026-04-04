"""Add page_count to documents.

Revision ID: 018
Revises: 017
"""

import sqlalchemy as sa

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("page_count", sa.Integer, nullable=True, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("documents", "page_count")
