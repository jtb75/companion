"""Rebrand config category enum: arlo_persona -> dd_persona, arlo_voice -> dd_voice

Revision ID: 006
Revises: 005
"""

from alembic import op

revision = "006"
down_revision = "005"


def upgrade() -> None:
    # Add new enum values
    op.execute("ALTER TYPE configcategory ADD VALUE IF NOT EXISTS 'DD_PERSONA'")
    op.execute("ALTER TYPE configcategory ADD VALUE IF NOT EXISTS 'DD_VOICE'")


def downgrade() -> None:
    # PG enums can't easily remove values; leave them in place
    pass
