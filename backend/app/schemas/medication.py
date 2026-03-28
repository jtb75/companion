from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MedicationCreate(BaseModel):
    name: str = Field(description="Medication name")
    dosage: str = Field(description="Dosage amount and unit (e.g. '10mg')")
    frequency: str = Field(description="How often to take (e.g. 'twice daily')")
    schedule: list[str] = Field(
        description="Scheduled times (e.g. ['08:00', '20:00'])",
    )
    pharmacy: str | None = Field(default=None, description="Pharmacy name or location")
    prescriber: str | None = Field(default=None, description="Prescribing doctor")
    refill_due_at: date | None = Field(default=None, description="Next refill date")


class MedicationUpdate(BaseModel):
    name: str | None = Field(default=None, description="Medication name")
    dosage: str | None = Field(default=None, description="Dosage amount and unit")
    frequency: str | None = Field(default=None, description="How often to take")
    schedule: list[str] | None = Field(default=None, description="List of scheduled times")
    pharmacy: str | None = Field(default=None, description="Pharmacy name or location")
    prescriber: str | None = Field(default=None, description="Prescribing doctor")
    refill_due_at: date | None = Field(default=None, description="Next refill date")
    is_active: bool | None = Field(
        default=None,
        description="Whether medication is currently active",
    )


class MedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    dosage: str
    frequency: str
    schedule: dict
    pharmacy: str | None = None
    prescriber: str | None = None
    refill_due_at: date | None = None
    is_active: bool
    created_at: datetime


class MedicationConfirmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scheduled_at: datetime
    confirmed_at: datetime | None = None
    missed: bool


class MedicationHistoryResponse(BaseModel):
    confirmations: list[MedicationConfirmResponse]
