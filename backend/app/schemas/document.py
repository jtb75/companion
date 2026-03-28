from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    DocumentClassification,
    DocumentStatus,
    RoutingDestination,
    SourceChannel,
    UrgencyLevel,
)
from app.schemas.common import PaginatedResponse


class DocumentScanRequest(BaseModel):
    source_channel: SourceChannel = Field(
        description="How the document was captured"
    )
    source_metadata: dict | None = Field(
        default=None,
        description="Source-specific metadata (raw_text, email headers, etc.)",
    )


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_channel: SourceChannel
    classification: DocumentClassification | None = None
    confidence_score: Decimal | None = None
    urgency_level: UrgencyLevel | None = None
    extracted_fields: dict | None = None
    spoken_summary: str | None = None
    card_summary: str | None = None
    routing_destination: RoutingDestination | None = None
    status: DocumentStatus
    received_at: datetime
    processed_at: datetime | None = None
    acknowledged_at: datetime | None = None


class DocumentListResponse(PaginatedResponse):
    data: list[DocumentResponse]


class DocumentStatusUpdate(BaseModel):
    status: DocumentStatus = Field(description="New document status")
