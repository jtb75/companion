from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MemoryCategory, MemorySource


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    preferred_name: str
    display_name: str
    date_of_birth: date | None = None
    primary_language: str
    voice_id: str
    pace_setting: str
    warmth_level: str
    nickname: str | None = None
    quiet_start: time | None = None
    quiet_end: time | None = None
    checkin_time: time | None = None
    away_mode: bool
    created_at: datetime


class UserUpdate(BaseModel):
    preferred_name: str | None = Field(default=None, description="User's preferred first name")
    display_name: str | None = Field(default=None, description="User's display name")
    date_of_birth: date | None = Field(default=None, description="Date of birth")
    primary_language: str | None = Field(default=None, description="Language code")
    voice_id: str | None = Field(default=None, description="D.D. voice ID")
    pace_setting: str | None = Field(default=None, description="Pace: slow/normal/fast")
    warmth_level: str | None = Field(default=None, description="Warmth: warm/neutral/professional")
    nickname: str | None = Field(default=None, description="What D.D. calls the user")
    quiet_start: time | None = Field(default=None, description="Quiet hours start")
    quiet_end: time | None = Field(default=None, description="Quiet hours end")
    checkin_time: time | None = Field(default=None, description="Daily check-in time")
    away_mode: bool | None = Field(default=None, description="Enable away mode")
    away_expires_at: datetime | None = Field(default=None, description="Away mode expiry")


class FunctionalMemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: MemoryCategory
    key: str
    value: dict
    source: MemorySource
    created_at: datetime
    updated_at: datetime


class UserMemoryResponse(BaseModel):
    memories: list[FunctionalMemoryResponse]
