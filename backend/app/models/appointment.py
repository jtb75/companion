import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    appointment_at: Mapped[datetime] = mapped_column(nullable=False)
    travel_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    preparation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user = relationship("User", back_populates="appointments")
    source_document = relationship("Document", back_populates="appointments")
