import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import QuestionContextType, QuestionStatus, UrgencyLevel


class QuestionTracker(Base):
    __tablename__ = "questions_tracker"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_type: Mapped[QuestionContextType] = mapped_column(nullable=False)
    context_ref_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    urgency_level: Mapped[UrgencyLevel] = mapped_column(
        nullable=False, default=UrgencyLevel.ROUTINE
    )
    escalation_threshold_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=24
    )
    asked_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="now()"
    )
    responded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[QuestionStatus] = mapped_column(
        nullable=False, default=QuestionStatus.OPEN
    )

    # Relationships
    user = relationship("User", back_populates="questions")
