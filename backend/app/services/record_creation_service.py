"""Shared service for creating bills and appointments from extracted data."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.bill import Bill


async def create_bill_from_fields(
    db: AsyncSession,
    user_id: UUID,
    fields: dict,
    source_document_id: UUID | None = None,
) -> Bill | None:
    """Create a Bill record from extracted fields.

    Fields expected: sender, amount_due, due_date,
    account_number_masked (optional).
    """
    sender = fields.get("sender")
    amount = fields.get("amount_due")
    due_date_str = fields.get("due_date")

    if not sender or not amount:
        return None

    # Delete existing bill from same document (idempotent)
    if source_document_id:
        await db.execute(
            delete(Bill).where(
                Bill.source_document_id == source_document_id
            )
        )

    # Parse due date
    due: date | None = None
    if due_date_str:
        for fmt in (
            "%Y-%m-%d",
            "%m/%d/%Y", "%m-%d-%Y",
            "%B %d, %Y", "%b %d, %Y",
        ):
            try:
                due = datetime.strptime(
                    due_date_str, fmt
                ).date()
                break
            except ValueError:
                continue

    if due is None:
        due = date.today() + timedelta(days=30)

    bill = Bill(
        user_id=user_id,
        sender=sender,
        description=f"Bill from {sender}",
        amount=Decimal(str(amount)),
        due_date=due,
        account_number_masked=fields.get(
            "account_number_masked"
        ),
        source_document_id=source_document_id,
    )
    db.add(bill)
    await db.flush()
    return bill


async def create_appointment_from_fields(
    db: AsyncSession,
    user_id: UUID,
    fields: dict,
    source_document_id: UUID | None = None,
) -> Appointment | None:
    """Create an Appointment from extracted fields.

    Fields expected: provider, date_time (optional),
    preparation_instructions (optional).
    """
    provider = fields.get("provider")
    date_time_str = fields.get("date_time")

    if not provider:
        return None

    # Delete existing appointment from same document
    if source_document_id:
        await db.execute(
            delete(Appointment).where(
                Appointment.source_document_id
                == source_document_id
            )
        )

    # Parse appointment datetime
    appt_dt: datetime | None = None
    if date_time_str:
        for fmt in (
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y",
            "%B %d, %Y at %I:%M %p",
        ):
            try:
                appt_dt = datetime.strptime(date_time_str, fmt)
                break
            except ValueError:
                continue

    if appt_dt is None:
        appt_dt = datetime.combine(
            date.today() + timedelta(days=7),
            datetime.min.time(),
        )

    appt = Appointment(
        user_id=user_id,
        provider_name=provider,
        appointment_at=appt_dt,
        preparation_notes=fields.get(
            "preparation_instructions"
        ),
        source_document_id=source_document_id,
    )
    db.add(appt)
    await db.flush()
    return appt
