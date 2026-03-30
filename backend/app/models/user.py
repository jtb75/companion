import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, Text, Time, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    preferred_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    primary_language: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="en"
    )

    # D.D. personality preferences
    voice_id: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="arlo_default"
    )
    pace_setting: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="normal"
    )
    warmth_level: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="warm"
    )
    nickname: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quiet hours
    quiet_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    quiet_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    checkin_time: Mapped[time | None] = mapped_column(
        Time, server_default=text("'09:00'")
    )

    # Away mode
    away_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    away_expires_at: Mapped[datetime | None] = mapped_column(
        nullable=True
    )

    # Care model & account status
    care_model: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="self_directed"
    )
    account_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="active"
    )

    # Relationships
    trusted_contacts = relationship(
        "TrustedContact", back_populates="user", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )
    medications = relationship(
        "Medication", back_populates="user", cascade="all, delete-orphan"
    )
    appointments = relationship(
        "Appointment", back_populates="user", cascade="all, delete-orphan"
    )
    bills = relationship(
        "Bill", back_populates="user", cascade="all, delete-orphan"
    )
    todos = relationship(
        "Todo", back_populates="user", cascade="all, delete-orphan"
    )
    questions = relationship(
        "QuestionTracker", back_populates="user", cascade="all, delete-orphan"
    )
    functional_memories = relationship(
        "FunctionalMemory", back_populates="user", cascade="all, delete-orphan"
    )
    caregiver_activity_logs = relationship(
        "CaregiverActivityLog", back_populates="user", cascade="all, delete-orphan"
    )
