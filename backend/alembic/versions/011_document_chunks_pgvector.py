"""Add document_chunks table with pgvector embedding support

Revision ID: 011
Revises: 010
"""

from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"


def _has_pgvector(connection) -> bool:
    """Check if pgvector extension is available."""
    result = connection.execute(
        sa.text(
            "SELECT 1 FROM pg_available_extensions "
            "WHERE name = 'vector'"
        )
    )
    return result.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    pgvector = _has_pgvector(conn)

    if pgvector:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("source_field", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default="now()",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add vector column via raw SQL (alembic doesn't know pgvector types)
    if pgvector:
        op.execute(
            "ALTER TABLE document_chunks "
            "ADD COLUMN embedding vector(768)"
        )

    op.create_index(
        "ix_document_chunks_user_id",
        "document_chunks",
        ["user_id"],
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
    )

    if pgvector:
        op.execute(
            "CREATE INDEX ix_document_chunks_embedding_hnsw "
            "ON document_chunks "
            "USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.drop_index("ix_document_chunks_document_id")
    op.drop_index("ix_document_chunks_user_id")
    op.drop_table("document_chunks")
