from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AppointmentCreate(BaseModel):
    provider_name: str = Field(description="Healthcare provider or office name")
    location: dict | None = Field(
        default=None,
        description="Location details (address, coordinates)",
    )
    appointment_at: datetime = Field(description="Date and time of the appointment")
    preparation_notes: str | None = Field(
        default=None,
        description="Instructions to prepare for the visit",
    )


class AppointmentUpdate(BaseModel):
    provider_name: str | None = Field(
        default=None, description="Provider name"
    )
    location: dict | None = Field(default=None, description="Location details")
    appointment_at: datetime | None = Field(
        default=None,
        description="Date and time of the appointment",
    )
    preparation_notes: str | None = Field(default=None, description="Preparation instructions")


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_name: str
    location: dict | None = None
    appointment_at: datetime
    travel_plan: dict | None = None
    reminder_sent: bool
    preparation_notes: str | None = None
    source_document_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
