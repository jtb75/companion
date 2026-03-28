from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CaregiverAction, UrgencyLevel


class CaregiverAlertResponse(BaseModel):
    alert_type: str
    urgency: UrgencyLevel
    message: str
    timestamp: datetime
    action_hint: str | None = None


class MedicationAdherenceSummary(BaseModel):
    total_scheduled: int
    total_confirmed: int
    total_missed: int
    adherence_rate: float


class CaregiverDashboardResponse(BaseModel):
    status_summary: str
    tasks_summary: dict
    medication_adherence: MedicationAdherenceSummary
    upcoming_bills: list[dict]
    upcoming_appointments: list[dict]
    active_urgent_items: list[dict]


class CaregiverActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: CaregiverAction
    details: dict | None = None
    occurred_at: datetime


class CollaborationCommentRequest(BaseModel):
    text: str = Field(description="Comment text")


class CollaborationResponse(BaseModel):
    scope_id: UUID
    resource_type: str
    expires_at: datetime | None = None
    comments: list[dict]
