from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConfigCategory, QuestionContextType, UrgencyLevel

# ---------------------------------------------------------------------------
# System config
# ---------------------------------------------------------------------------

class ConfigEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: ConfigCategory
    key: str
    value: dict
    description: str | None = None
    is_active: bool
    version: int
    updated_by: str
    updated_at: datetime


class ConfigCreateRequest(BaseModel):
    category: ConfigCategory = Field(description="Config category")
    key: str = Field(description="Config key within the category")
    value: dict = Field(description="JSON value for the config entry")
    description: str | None = Field(default=None, description="Human-readable description")


class ConfigUpdateRequest(BaseModel):
    value: dict = Field(description="New JSON value")
    reason: str | None = Field(default=None, description="Reason for the change")


class ConfigAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    config_id: UUID
    category: ConfigCategory
    key: str
    old_value: dict | None = None
    new_value: dict
    changed_by: str
    reason: str | None = None
    changed_at: datetime


# ---------------------------------------------------------------------------
# Pipeline health
# ---------------------------------------------------------------------------

class PipelineHealthResponse(BaseModel):
    documents_in_flight: int
    avg_processing_time_ms: float
    stages: dict
    last_24h: dict


class PipelineFailureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID | None = None
    stage: str
    error_message: str | None = None
    recorded_at: datetime


# ---------------------------------------------------------------------------
# Engagement metrics
# ---------------------------------------------------------------------------

class EngagementMetricsResponse(BaseModel):
    active_users: int
    session_frequency: float
    section_usage: dict


# ---------------------------------------------------------------------------
# Escalations
# ---------------------------------------------------------------------------

class EscalationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_text: str
    context_type: QuestionContextType
    urgency_level: UrgencyLevel
    hours_open: float
    threshold_hours: int


# ---------------------------------------------------------------------------
# Admin users
# ---------------------------------------------------------------------------

class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    role: str
    is_active: bool
    last_login_at: datetime | None = None


class AdminUserCreate(BaseModel):
    email: str = Field(description="Admin email address")
    name: str = Field(description="Admin display name")
    role: str = Field(default="viewer", description="Admin role: viewer, editor, or admin")
