from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentStatus


class BillCreate(BaseModel):
    sender: str = Field(description="Company or entity sending the bill")
    description: str | None = Field(default=None, description="Brief description of the bill")
    amount: Decimal = Field(description="Total amount due")
    due_date: date = Field(description="Payment due date")
    account_number_masked: str | None = Field(
        default=None,
        description="Masked account number (e.g. '****1234')",
    )


class BillUpdate(BaseModel):
    sender: str | None = Field(
        default=None,
        description="Company or entity sending the bill",
    )
    description: str | None = Field(default=None, description="Brief description")
    amount: Decimal | None = Field(default=None, description="Total amount due")
    due_date: date | None = Field(default=None, description="Payment due date")
    account_number_masked: str | None = Field(default=None, description="Masked account number")
    payment_status: PaymentStatus | None = Field(
        default=None,
        description="Current payment status",
    )


class BillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sender: str
    description: str | None = None
    amount: Decimal
    due_date: date
    account_number_masked: str | None = None
    payment_status: PaymentStatus
    source_document_id: UUID | None = None
    reminder_set: bool
    created_at: datetime
    updated_at: datetime


class BillSummaryResponse(BaseModel):
    total_due: Decimal
    upcoming_count: int
    overdue_count: int
    balance: Decimal | None = None
