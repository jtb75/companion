import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AccessTier, RelationshipType


class CaregiverAssignmentRequest(Base):
    __tablename__ = "caregiver_assignment_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    caregiver_email: Mapped[str] = mapped_column(Text, nullable=False)
    caregiver_name: Mapped[str] = mapped_column(Text, nullable=False)
    relationship_type: Mapped[RelationshipType] = mapped_column(nullable=False)
    access_tier: Mapped[AccessTier] = mapped_column(
        nullable=False, default=AccessTier.TIER_1
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="pending_approval"
    )
    initiated_by: Mapped[str] = mapped_column(Text, nullable=False)  # caregiver, member, admin
    initiated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="now()"
    )
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    member = relationship("User", foreign_keys=[member_id])
