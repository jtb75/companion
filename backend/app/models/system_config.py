import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ConfigCategory


class SystemConfig(TimestampMixin, Base):
    __tablename__ = "system_config"
    __table_args__ = (
        UniqueConstraint("category", "key", name="uq_system_config_category_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category: Mapped[ConfigCategory] = mapped_column(nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    updated_by: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    audit_logs = relationship(
        "ConfigAuditLog", back_populates="config", cascade="all, delete-orphan"
    )


class ConfigAuditLog(Base):
    __tablename__ = "config_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("system_config.id"),
        nullable=False,
    )
    category: Mapped[ConfigCategory] = mapped_column(nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_by: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default="now()"
    )

    # Relationships
    config = relationship("SystemConfig", back_populates="audit_logs")
