"""add reading_grade to documents

Revision ID: 016
Revises: 015
Create Date: 2026-04-02 05:15:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "reading_grade",
            sa.Numeric(precision=3, scale=1),
            nullable=True,
        ),
    )

def downgrade() -> None:
    op.drop_column('documents', 'reading_grade')
