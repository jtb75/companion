"""Convert encrypted columns from JSONB to Text.

Revision ID: 017
Revises: 016
"""

import sqlalchemy as sa

from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert JSONB columns to Text for field-level encryption
    # Existing data will be lost — run on fresh or staging DBs
    op.alter_column(
        "documents", "extracted_fields",
        type_=sa.Text,
        existing_type=sa.dialects.postgresql.JSONB,
        postgresql_using="extracted_fields::text",
    )
    op.alter_column(
        "pending_reviews", "proposed_record_data",
        type_=sa.Text,
        existing_type=sa.dialects.postgresql.JSONB,
        postgresql_using="proposed_record_data::text",
    )
    op.alter_column(
        "functional_memories", "value",
        type_=sa.Text,
        existing_type=sa.dialects.postgresql.JSONB,
        postgresql_using="value::text",
    )


def downgrade() -> None:
    op.alter_column(
        "documents", "extracted_fields",
        type_=sa.dialects.postgresql.JSONB,
        existing_type=sa.Text,
        postgresql_using="extracted_fields::jsonb",
    )
    op.alter_column(
        "pending_reviews", "proposed_record_data",
        type_=sa.dialects.postgresql.JSONB,
        existing_type=sa.Text,
        postgresql_using="proposed_record_data::jsonb",
    )
    op.alter_column(
        "functional_memories", "value",
        type_=sa.dialects.postgresql.JSONB,
        existing_type=sa.Text,
        postgresql_using="value::jsonb",
    )
