from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Standard wrapper for all events."""
    event_id: UUID = Field(default_factory=uuid4)
    event_name: str
    user_id: UUID
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    payload: dict


# ── Document events ─────────────────────────────────────────

class DocumentReceivedPayload(BaseModel):
    document_id: UUID
    source_channel: str
    raw_text_ref: str | None = None

class DocumentProcessedPayload(BaseModel):
    document_id: UUID
    classification: str
    confidence_score: float
    urgency_level: str
    extracted_fields: dict | None = None

class DocumentRoutedPayload(BaseModel):
    document_id: UUID
    routing_destination: str
    card_summary: str | None = None
    spoken_summary: str | None = None

# ── Question events ─────────────────────────────────────────

class QuestionAskedPayload(BaseModel):
    question_id: UUID
    question_text: str
    context_type: str
    context_ref_id: UUID | None = None
    urgency_level: str = "routine"

class QuestionAnsweredPayload(BaseModel):
    question_id: UUID
    answer_source: str

class QuestionThresholdCrossedPayload(BaseModel):
    question_id: UUID
    hours_open: float
    escalation_threshold_hours: int
    trusted_contact_ids: list[UUID]

# ── Medication events ───────────────────────────────────────

class MedicationConfirmedPayload(BaseModel):
    confirmation_id: UUID
    medication_id: UUID
    scheduled_at: datetime
    confirmed_at: datetime

class MedicationMissedPayload(BaseModel):
    confirmation_id: UUID
    medication_id: UUID
    scheduled_at: datetime

# ── Bill events ─────────────────────────────────────────────

class BillAcknowledgedPayload(BaseModel):
    bill_id: UUID
    user_id: UUID

class BillOverduePayload(BaseModel):
    bill_id: UUID
    sender: str
    amount: Decimal
    due_date: str  # ISO date
    days_overdue: int

# ── Trip events ─────────────────────────────────────────────

class TripStartedPayload(BaseModel):
    appointment_id: UUID
    travel_plan: dict | None = None
    depart_at: datetime | None = None

class TripCompletedPayload(BaseModel):
    appointment_id: UUID
    arrived_at: datetime

# ── Away mode events ────────────────────────────────────────

class AwayModeSetPayload(BaseModel):
    user_id: UUID
    away_expires_at: datetime | None = None

class AwayModeExtendedPayload(BaseModel):
    user_id: UUID
    previous_expires_at: datetime | None = None
    new_expires_at: datetime | None = None

# ── Memory events ───────────────────────────────────────────

class MemoryUpdatedPayload(BaseModel):
    memory_id: UUID
    category: str
    key: str
    source: str

class MemoryDeletedPayload(BaseModel):
    memory_id: UUID
    category: str
    key: str
    reason: str

# ── Caregiver events ────────────────────────────────────────

class CaregiverAlertTriggeredPayload(BaseModel):
    trusted_contact_id: UUID
    alert_type: str
    context: dict | None = None

class CaregiverDashboardViewedPayload(BaseModel):
    trusted_contact_id: UUID
    user_id: UUID
    sections_viewed: list[str] | None = None

# ── Notification events ─────────────────────────────────────

class NotificationDeliveredPayload(BaseModel):
    notification_id: UUID
    channel: str
    user_id: UUID
    content_type: str

class NotificationDismissedPayload(BaseModel):
    notification_id: UUID
    user_id: UUID
    dismissed_at: datetime

# ── Check-in events ─────────────────────────────────────────

class CheckinMorningTriggeredPayload(BaseModel):
    user_id: UUID
    checkin_time: str
    items_count: int
    briefing: str | None = None

class CheckinMorningAcknowledgedPayload(BaseModel):
    user_id: UUID
    acknowledged_at: datetime
    items_reviewed: int

# ── Config events ───────────────────────────────────────────

class ConfigUpdatedPayload(BaseModel):
    config_id: UUID
    category: str
    key: str
    old_value: dict | None = None
    new_value: dict
    changed_by: str


# Map event names to their payload types
EVENT_PAYLOAD_MAP: dict[str, type[BaseModel]] = {
    "document.received": DocumentReceivedPayload,
    "document.processed": DocumentProcessedPayload,
    "document.routed": DocumentRoutedPayload,
    "question.asked": QuestionAskedPayload,
    "question.answered": QuestionAnsweredPayload,
    "question.threshold_crossed": QuestionThresholdCrossedPayload,
    "medication.confirmed": MedicationConfirmedPayload,
    "medication.missed": MedicationMissedPayload,
    "bill.acknowledged": BillAcknowledgedPayload,
    "bill.overdue": BillOverduePayload,
    "trip.started": TripStartedPayload,
    "trip.completed": TripCompletedPayload,
    "away.mode.set": AwayModeSetPayload,
    "away.mode.extended": AwayModeExtendedPayload,
    "memory.updated": MemoryUpdatedPayload,
    "memory.deleted": MemoryDeletedPayload,
    "caregiver.alert.triggered": CaregiverAlertTriggeredPayload,
    "caregiver.dashboard.viewed": CaregiverDashboardViewedPayload,
    "notification.delivered": NotificationDeliveredPayload,
    "notification.dismissed": NotificationDismissedPayload,
    "checkin.morning.triggered": CheckinMorningTriggeredPayload,
    "checkin.morning.acknowledged": CheckinMorningAcknowledgedPayload,
    "config.updated": ConfigUpdatedPayload,
}
