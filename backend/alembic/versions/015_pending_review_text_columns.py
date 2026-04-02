"""Convert pending_reviews enum columns to text.

Revision ID: 015
Revises: 014
"""

from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE pending_reviews
            ALTER COLUMN review_status TYPE text
                USING review_status::text,
            ALTER COLUMN recommended_action TYPE text
                USING recommended_action::text
    """)


def downgrade() -> None:
    pass
