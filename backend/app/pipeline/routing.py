"""Stage 5 — Routes documents to the correct app section and creates records."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.bill import Bill
from app.pipeline.schemas import (
    ClassificationResult,
    ExtractionResult,
    RoutingResult,
    SummarizationResult,
)

# Routing table from the spec
ROUTING_TABLE: dict[str, str] = {
    "bill": "bills",
    "medical": "my_health",
    "legal": "home",
    "government": "home",
    "insurance": "my_health",
    "form": "home",
    "junk": "home",  # archived, not surfaced
    "personal": "home",
    "unknown": "home",
}


async def route(
    db: AsyncSession,
    user_id: UUID,
    classification: ClassificationResult,
    extraction: ExtractionResult,
    summarization: SummarizationResult,
) -> RoutingResult:
    """Route document to correct section and create linked records."""

    destination = ROUTING_TABLE.get(classification.classification, "home")
    records_created: list[dict] = []
    suggested_action: str | None = None

    # Create linked records based on document type
    if classification.classification == "bill":
        record = await _create_bill_record(
            db, user_id, classification.document_id, extraction.extracted_fields
        )
        if record:
            records_created.append({"type": "bill", "id": str(record.id)})
            amount = extraction.extracted_fields.get("amount_due", "?")
            due = extraction.extracted_fields.get("due_date", "soon")
            suggested_action = f"Pay ${amount} — due {due}"

    elif classification.classification == "medical":
        record = await _create_appointment_record(
            db, user_id, classification.document_id, extraction.extracted_fields
        )
        if record:
            records_created.append({"type": "appointment", "id": str(record.id)})
            provider = extraction.extracted_fields.get("provider", "your doctor")
            suggested_action = f"Check appointment with {provider}"

    elif classification.classification == "legal":
        suggested_action = "Review this with your trusted contact"

    elif classification.classification == "junk":
        suggested_action = None  # no action for junk

    return RoutingResult(
        document_id=classification.document_id,
        routing_destination=destination,
        suggested_action=suggested_action,
        records_created=records_created,
    )


async def _create_bill_record(
    db: AsyncSession, user_id: UUID, document_id: UUID, fields: dict
) -> Bill | None:
    """Create a Bill record from extracted document fields."""
    sender = fields.get("sender")
    amount = fields.get("amount_due")
    due_date_str = fields.get("due_date")

    if not sender or not amount:
        return None

    # Parse due date if available
    due: date | None = None
    if due_date_str:
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y"):
            try:
                due = datetime.strptime(due_date_str, fmt).date()
                break
            except ValueError:
                continue

    if due is None:
        due = date.today() + timedelta(days=30)  # default 30 days

    bill = Bill(
        user_id=user_id,
        sender=sender,
        description=f"Bill from {sender}",
        amount=Decimal(str(amount)),
        due_date=due,
        account_number_masked=fields.get("account_number_masked"),
        source_document_id=document_id,
    )
    db.add(bill)
    await db.flush()
    return bill


async def _create_appointment_record(
    db: AsyncSession, user_id: UUID, document_id: UUID, fields: dict
) -> Appointment | None:
    """Create an Appointment record from extracted document fields."""
    provider = fields.get("provider")
    date_time_str = fields.get("date_time")

    if not provider:
        return None

    # Parse appointment datetime
    appt_dt: datetime | None = None
    if date_time_str:
        for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y", "%B %d, %Y at %I:%M %p"):
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
        preparation_notes=fields.get("preparation_instructions"),
        source_document_id=document_id,
    )
    db.add(appt)
    await db.flush()
    return appt
