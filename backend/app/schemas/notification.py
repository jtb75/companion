from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UrgencyLevel


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    message: str
    urgency: UrgencyLevel
    created_at: datetime
    acknowledged_at: datetime | None = None


class NotificationPreferencesResponse(BaseModel):
    quiet_start: time | None = None
    quiet_end: time | None = None
    checkin_time: time | None = None


class NotificationPreferencesUpdate(BaseModel):
    quiet_start: time | None = Field(default=None, description="Start of quiet hours (HH:MM)")
    quiet_end: time | None = Field(default=None, description="End of quiet hours (HH:MM)")
    checkin_time: time | None = Field(default=None, description="Daily check-in time (HH:MM)")
