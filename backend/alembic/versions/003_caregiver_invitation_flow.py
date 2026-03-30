"""Add caregiver invitation and assignment flow

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"


def upgrade() -> None:
    # -- User table: care_model and account_status --
    op.add_column("users", sa.Column("care_model", sa.Text(), nullable=False, server_default="self_directed"))
    op.add_column("users", sa.Column("account_status", sa.Text(), nullable=False, server_default="active"))

    # -- TrustedContact table: invitation tracking --
    op.add_column("trusted_contacts", sa.Column("invitation_status", sa.Text(), nullable=False, server_default="accepted"))
    op.add_column("trusted_contacts", sa.Column("invitation_token", sa.Text(), nullable=True))
    op.add_column("trusted_contacts", sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("trusted_contacts", sa.Column("invited_by_admin_id", UUID(as_uuid=True), nullable=True))
    op.add_column("trusted_contacts", sa.Column("invited_by_user_id", UUID(as_uuid=True), nullable=True))
    op.add_column("trusted_contacts", sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True))

    op.create_unique_constraint("uq_trusted_contacts_invitation_token", "trusted_contacts", ["invitation_token"])
    op.create_foreign_key("fk_trusted_contacts_invited_by_admin", "trusted_contacts", "admin_users", ["invited_by_admin_id"], ["id"])
    op.create_foreign_key("fk_trusted_contacts_invited_by_user", "trusted_contacts", "users", ["invited_by_user_id"], ["id"], ondelete="SET NULL")

    # -- New table: caregiver_assignment_requests --
    op.create_table(
        "caregiver_assignment_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("member_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("caregiver_email", sa.Text(), nullable=False),
        sa.Column("caregiver_name", sa.Text(), nullable=False),
        sa.Column("relationship_type", sa.Text(), nullable=False),
        sa.Column("access_tier", sa.Text(), nullable=False, server_default="tier_1"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending_approval"),
        sa.Column("initiated_by", sa.Text(), nullable=False),
        sa.Column("initiated_by_admin_id", UUID(as_uuid=True), sa.ForeignKey("admin_users.id"), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assignment_requests_member_status", "caregiver_assignment_requests", ["member_id", "status"])


def downgrade() -> None:
    op.drop_table("caregiver_assignment_requests")

    op.drop_constraint("fk_trusted_contacts_invited_by_user", "trusted_contacts", type_="foreignkey")
    op.drop_constraint("fk_trusted_contacts_invited_by_admin", "trusted_contacts", type_="foreignkey")
    op.drop_constraint("uq_trusted_contacts_invitation_token", "trusted_contacts", type_="unique")
    op.drop_column("trusted_contacts", "accepted_at")
    op.drop_column("trusted_contacts", "invited_by_user_id")
    op.drop_column("trusted_contacts", "invited_by_admin_id")
    op.drop_column("trusted_contacts", "invited_at")
    op.drop_column("trusted_contacts", "invitation_token")
    op.drop_column("trusted_contacts", "invitation_status")

    op.drop_column("users", "account_status")
    op.drop_column("users", "care_model")
