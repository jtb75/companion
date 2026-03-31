"""Drop unique constraint on users.phone

Revision ID: 005
Revises: 004
"""

from alembic import op

revision = "005"
down_revision = "004"


def upgrade() -> None:
    op.drop_constraint("users_phone_key", "users", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("users_phone_key", "users", ["phone"])
