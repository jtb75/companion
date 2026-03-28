import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PipelineMetric(Base):
    __tablename__ = "pipeline_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=True,
    )
    stage: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="now()"
    )

    # Relationships
    document = relationship("Document", back_populates="pipeline_metrics")
