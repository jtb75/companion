"""Add pending_reviews table and related enums.

Revision ID: 013
Revises: 012
"""

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add PENDING_REVIEW to documentstatus enum (uppercase to match existing values)
    op.execute(
        "ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS"
        " 'PENDING_REVIEW'"
    )
    # Also add lowercase in case it was already created
    op.execute(
        "ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS"
        " 'pending_review'"
    )

    # Create enum types and table via raw SQL for full control
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
                'review_with_contact', 'file_only',
                'discard'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS pending_reviews (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL
                REFERENCES users(id) ON DELETE CASCADE,
            document_id UUID
                REFERENCES documents(id) ON DELETE SET NULL,
            review_status reviewstatus NOT NULL
                DEFAULT 'pending',
            recommended_action recommendedaction NOT NULL,
            proposed_record_data JSONB NOT NULL,
            confidence_score NUMERIC(4, 3),
            source_description TEXT NOT NULL
                DEFAULT 'a document',
            is_urgent BOOLEAN NOT NULL DEFAULT false,
            is_past_due BOOLEAN NOT NULL DEFAULT false,
            is_duplicate BOOLEAN NOT NULL DEFAULT false,
            duplicate_of_id UUID,
            presented_at TIMESTAMP,
            resolved_at TIMESTAMP,
            created_record_type TEXT,
            created_record_id UUID,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """)

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
