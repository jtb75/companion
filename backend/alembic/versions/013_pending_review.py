"""Add pending_reviews table and related enums.

Revision ID: 013
Revises: 012
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new enum types (using DO blocks for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE reviewstatus AS ENUM (
                'pending', 'presented', 'confirmed',
                'skipped', 'expired', 'auto_created'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE recommendedaction AS ENUM (
                'add_bill', 'add_appointment',
                'review_with_contact', 'file_only', 'discard'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # Add pending_review to documentstatus enum
    op.execute(
        "ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS 'pending_review'"
    )

    # Create pending_reviews table (use sa.Text for enum columns
    # since enum types are created above via raw SQL)
    op.create_table(
        "pending_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id", UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "review_status",
            sa.Enum(
                "pending", "presented", "confirmed",
                "skipped", "expired", "auto_created",
                name="reviewstatus",
                create_type=False,
            ),
            nullable=False, server_default="pending",
        ),
        sa.Column(
            "recommended_action",
            sa.Enum(
                "add_bill", "add_appointment",
                "review_with_contact", "file_only", "discard",
                name="recommendedaction",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("proposed_record_data", JSONB, nullable=False),
        sa.Column(
            "confidence_score", sa.Numeric(4, 3), nullable=True
        ),
        sa.Column(
            "source_description", sa.Text,
            nullable=False, server_default="a document",
        ),
        sa.Column(
            "is_urgent", sa.Boolean,
            nullable=False, server_default="false",
        ),
        sa.Column(
            "is_past_due", sa.Boolean,
            nullable=False, server_default="false",
        ),
        sa.Column(
            "is_duplicate", sa.Boolean,
            nullable=False, server_default="false",
        ),
        sa.Column(
            "duplicate_of_id", UUID(as_uuid=True), nullable=True
        ),
        sa.Column("presented_at", sa.DateTime, nullable=True),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("created_record_type", sa.Text, nullable=True),
        sa.Column(
            "created_record_id", UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime,
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime,
            nullable=False, server_default=sa.func.now(),
        ),
    )

    # Index for querying pending reviews by user
    op.create_index(
        "ix_pending_reviews_user_status",
        "pending_reviews",
        ["user_id", "review_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_pending_reviews_user_status")
    op.drop_table("pending_reviews")
    op.execute("DROP TYPE IF EXISTS reviewstatus")
    op.execute("DROP TYPE IF EXISTS recommendedaction")
