"""Add related_bill_id to todos

Revision ID: 019
Revises: 018
"""

import sqlalchemy as sa
from alembic import op

revision = "019"
down_revision = "018"


def upgrade() -> None:
    op.add_column(
        "todos",
        sa.Column(
            "related_bill_id",
            sa.UUID(),
            sa.ForeignKey("bills.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("todos", "related_bill_id")
