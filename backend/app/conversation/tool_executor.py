"""Execute Gemini function calls against the service layer."""

import logging
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.bill import Bill
from app.models.enums import PaymentStatus
from app.models.medication import (
    Medication,
    MedicationConfirmation,
)
from app.models.todo import Todo
from app.services.section_service import get_today_section

logger = logging.getLogger(__name__)


async def execute_tool(
    function_name: str,
    arguments: dict,
    db: AsyncSession,
    user_id: UUID,
) -> dict:
    """Dispatch a tool call to the right handler."""
    handlers = {
        "list_medications": _list_medications,
        "list_bills": _list_bills,
        "list_appointments": _list_appointments,
        "list_todos": _list_todos,
        "get_today_summary": _get_today_summary,
        "mark_bill_paid": _mark_bill_paid,
        "confirm_medication_taken": _confirm_med,
        "add_appointment": _add_appointment,
        "add_todo": _add_todo,
        "complete_todo": _complete_todo,
        "get_pending_reviews": _get_pending_reviews,
        "confirm_document_action": _confirm_document_action,
        "update_review_fields": _update_review_fields,
    }
    handler = handlers.get(function_name)
    if handler is None:
        return {
            "error": True,
            "message": f"Unknown tool: {function_name}",
        }
    try:
        return await handler(db, user_id, arguments)
    except Exception:
        logger.exception(
            "Tool %s failed for user %s",
            function_name,
            user_id,
        )
        return {
            "error": True,
            "message": (
                f"Failed to execute {function_name}."
            ),
        }


# ── Lookup handlers ──────────────────────────────────


async def _list_medications(
    db: AsyncSession, user_id: UUID, _args: dict
) -> dict:
    result = await db.execute(
        select(Medication).where(
            Medication.user_id == user_id,
            Medication.is_active.is_(True),
        )
    )
    meds = result.scalars().all()
    return {
        "medications": [
            {
                "id": str(m.id),
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
            }
            for m in meds
        ],
    }


async def _list_bills(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    stmt = select(Bill).where(Bill.user_id == user_id)
    status_filter = args.get("status")
    if status_filter:
        stmt = stmt.where(
            Bill.payment_status == status_filter
        )
    stmt = stmt.order_by(Bill.due_date)
    result = await db.execute(stmt)
    bills = result.scalars().all()
    return {
        "bills": [
            {
                "id": str(b.id),
                "sender": b.sender,
                "amount": str(b.amount),
                "due_date": b.due_date.isoformat(),
                "status": str(b.payment_status),
            }
            for b in bills
        ],
    }


async def _list_appointments(
    db: AsyncSession, user_id: UUID, _args: dict
) -> dict:
    now = datetime.utcnow()
    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.user_id == user_id,
            Appointment.appointment_at >= now,
        )
        .order_by(Appointment.appointment_at)
    )
    appts = result.scalars().all()
    return {
        "appointments": [
            {
                "id": str(a.id),
                "provider": a.provider_name,
                "at": a.appointment_at.isoformat(),
                "notes": a.preparation_notes or "",
            }
            for a in appts
        ],
    }


async def _list_todos(
    db: AsyncSession, user_id: UUID, _args: dict
) -> dict:
    result = await db.execute(
        select(Todo)
        .where(
            Todo.user_id == user_id,
            Todo.is_active.is_(True),
            Todo.completed_at.is_(None),
        )
        .order_by(Todo.due_date.asc().nulls_last())
    )
    todos = result.scalars().all()
    return {
        "todos": [
            {
                "id": str(t.id),
                "title": t.title,
                "due_date": (
                    t.due_date.isoformat()
                    if t.due_date
                    else None
                ),
                "category": str(t.category),
            }
            for t in todos
        ],
    }


async def _get_today_summary(
    db: AsyncSession, user_id: UUID, _args: dict
) -> dict:
    return await get_today_section(db, user_id)


# ── Action handlers ──────────────────────────────────


async def _mark_bill_paid(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    bill_id = UUID(args["bill_id"])
    result = await db.execute(
        select(Bill).where(
            Bill.id == bill_id,
            Bill.user_id == user_id,
        )
    )
    bill = result.scalar_one_or_none()
    if bill is None:
        return {
            "error": True,
            "message": "Bill not found.",
        }
    bill.payment_status = PaymentStatus.PAID
    await db.flush()
    return {
        "success": True,
        "bill_id": str(bill.id),
        "sender": bill.sender,
        "amount": str(bill.amount),
    }


async def _confirm_med(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    med_id = UUID(args["medication_id"])
    result = await db.execute(
        select(Medication).where(
            Medication.id == med_id,
            Medication.user_id == user_id,
        )
    )
    med = result.scalar_one_or_none()
    if med is None:
        return {
            "error": True,
            "message": "Medication not found.",
        }
    confirmation = MedicationConfirmation(
        medication_id=med_id,
        scheduled_at=datetime.utcnow(),
        confirmed_at=datetime.utcnow(),
        missed=False,
    )
    db.add(confirmation)
    await db.flush()
    return {
        "success": True,
        "medication": med.name,
        "confirmed_at": (
            confirmation.confirmed_at.isoformat()
        ),
    }


async def _add_appointment(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    appt = Appointment(
        user_id=user_id,
        provider_name=args["provider_name"],
        appointment_at=datetime.fromisoformat(
            args["appointment_at"]
        ),
        preparation_notes=args.get("preparation_notes"),
    )
    db.add(appt)
    await db.commit()
    
    return {
        "success": True,
        "id": str(appt.id),
        "provider": appt.provider_name,
        "at": appt.appointment_at.isoformat(),
        "requires_confirmation": True,
        "confirmation_message": (
            f"Add appointment with {appt.provider_name} "
            f"on {appt.appointment_at.strftime('%B %d')}?"
        ),
    }


async def _add_todo(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    from app.models.enums import TodoCategory, TodoSource
    
    due = None
    if args.get("due_date"):
        try:
            due = date.fromisoformat(args["due_date"])
        except ValueError:
            pass

    todo = Todo(
        user_id=user_id,
        title=args["title"],
        due_date=due,
        category=args.get("category", TodoCategory.GENERAL),
        source=TodoSource.ARLO_SUGGESTION,
    )
    db.add(todo)
    await db.commit()
    
    logger.info(
        "TOOL_CALL: add_todo successful for user %s: %s",
        user_id, todo.title
    )
    
    return {
        "success": True,
        "id": str(todo.id),
        "title": todo.title,
        "requires_confirmation": True,
        "confirmation_message": f"Add '{todo.title}' to your list?",
    }


async def _complete_todo(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    todo_id = UUID(args["todo_id"])
    result = await db.execute(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == user_id,
        )
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        return {
            "error": True,
            "message": "Todo not found.",
        }
    todo.completed_at = datetime.utcnow()
    todo.is_active = False
    await db.flush()
    return {
        "success": True,
        "id": str(todo.id),
        "title": todo.title,
        "requires_confirmation": True,
        "confirmation_message": f"Add '{todo.title}' to your list?",
    }


# ── Document review tools ──


async def _resolve_review_id(
    db: AsyncSession, user_id: UUID, raw_id: str
) -> UUID | None:
    """Resolve a review ID from various formats.

    Accepts: short ID ("1"), full UUID, or garbage.
    Falls back to the most recent pending review.
    """
    from app.models.pending_review import PendingReview

    # Try as a short numeric ID (index into pending list)
    if raw_id.isdigit():
        idx = int(raw_id) - 1  # 1-based
        result = await db.execute(
            select(PendingReview).where(
                PendingReview.user_id == user_id,
                PendingReview.review_status.in_(
                    ["pending", "presented"]
                ),
            ).order_by(
                PendingReview.is_urgent.desc(),
                PendingReview.created_at,
            )
        )
        reviews = result.scalars().all()
        if 0 <= idx < len(reviews):
            return reviews[idx].id

    # Try as UUID
    try:
        return UUID(raw_id)
    except (ValueError, AttributeError):
        pass

    # Fallback: most recent pending review
    result = await db.execute(
        select(PendingReview).where(
            PendingReview.user_id == user_id,
            PendingReview.review_status.in_(
                ["pending", "presented"]
            ),
        ).order_by(
            PendingReview.is_urgent.desc(),
            PendingReview.created_at.desc(),
        ).limit(1)
    )
    review = result.scalar_one_or_none()
    return review.id if review else None


async def _get_pending_reviews(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    from app.models.document import Document
    from app.models.enums import ReviewStatus
    from app.models.pending_review import PendingReview

    result = await db.execute(
        select(PendingReview)
        .where(
            PendingReview.user_id == user_id,
            PendingReview.review_status.in_(
                [ReviewStatus.PENDING, ReviewStatus.PRESENTED]
            ),
        )
        .order_by(
            PendingReview.is_urgent.desc(),
            PendingReview.created_at,
        )
        .limit(5)
    )
    reviews = result.scalars().all()

    items = []
    for i, r in enumerate(reviews, 1):
        doc = await db.get(Document, r.document_id) if r.document_id else None
        # Get document content for full context
        ocr_text = ""
        if doc:
            # Try OCR text first
            if doc.source_metadata:
                ocr_text = doc.source_metadata.get(
                    "ocr_text", ""
                )
            # Fallback to extracted fields as content source
            if not ocr_text and doc.extracted_fields:
                import json
                ocr_text = json.dumps(
                    doc.extracted_fields, indent=2
                )
        ocr_text = ocr_text[:1500]  # Generous context
        logger.info(
            "REVIEW_DATA: doc=%s spoken=%s text_len=%d",
            r.document_id,
            bool(doc.spoken_summary if doc else None),
            len(ocr_text),
        )

        items.append({
            "review_id": str(i),
            "review_uuid": str(r.id),
            "source": r.source_description,
            "recommended_action": r.recommended_action,
            "proposed_data": r.proposed_record_data,
            "confidence": (
                float(r.confidence_score)
                if r.confidence_score else None
            ),
            "is_urgent": r.is_urgent,
            "is_past_due": r.is_past_due,
            "is_duplicate": r.is_duplicate,
            "card_summary": doc.card_summary if doc else None,
            "spoken_summary": (
                r.proposed_record_data.get("_spoken_summary")
                or (doc.spoken_summary if doc else None)
            ),
            "document_text": ocr_text,
            "classification": (
                getattr(
                    doc.classification, "value",
                    str(doc.classification),
                )
                if doc and doc.classification else None
            ),
        })

        # Mark as presented
        if r.review_status == ReviewStatus.PENDING:
            r.review_status = ReviewStatus.PRESENTED
            r.presented_at = datetime.utcnow()

    await db.flush()
    return {"reviews": items, "count": len(items)}


async def _confirm_document_action(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    from app.models.enums import RecommendedAction, ReviewStatus
    from app.models.pending_review import PendingReview
    from app.services.record_creation_service import (
        create_appointment_from_fields,
        create_bill_from_fields,
    )

    raw_id = str(args.get("review_id", "")).strip()
    action = args.get("action", "confirm")

    # Resolve review_id — could be a short ID ("1"),
    # a UUID, or garbage from Gemini
    review_id = await _resolve_review_id(
        db, user_id, raw_id
    )
    if review_id is None:
        return {
            "error": True,
            "message": "No pending reviews found.",
        }

    result = await db.execute(
        select(PendingReview).where(
            PendingReview.id == review_id,
            PendingReview.user_id == user_id,
        )
    )
    review = result.scalar_one_or_none()
    if review is None:
        return {"error": True, "message": "Review not found."}

    async def _get_remaining_count() -> int:
        from sqlalchemy import func
        count_res = await db.execute(
            select(func.count()).select_from(PendingReview).where(
                PendingReview.user_id == user_id,
                PendingReview.review_status.in_(
                    [ReviewStatus.PENDING, ReviewStatus.PRESENTED]
                ),
            )
        )
        return int(count_res.scalar() or 0)

    if action == "skip":
        review.review_status = ReviewStatus.SKIPPED
        review.resolved_at = datetime.utcnow()
        await db.flush()
        return {
            "success": True,
            "action": "skipped",
            "remaining_count": await _get_remaining_count(),
        }

    fields = review.proposed_record_data or {}
    rec_action = review.recommended_action

    if rec_action == RecommendedAction.ADD_BILL:
        if action == "mark_paid":
            bill = await create_bill_from_fields(
                db, user_id, fields,
                source_document_id=review.document_id,
            )
            if bill:
                from app.models.enums import PaymentStatus
                bill.payment_status = PaymentStatus.PAID
                await db.flush()
                review.created_record_type = "bill"
                review.created_record_id = bill.id
        else:
            bill = await create_bill_from_fields(
                db, user_id, fields,
                source_document_id=review.document_id,
            )
            if bill:
                review.created_record_type = "bill"
                review.created_record_id = bill.id

        review.review_status = ReviewStatus.CONFIRMED
        review.resolved_at = datetime.utcnow()
        await db.flush()

        sender = fields.get("sender", "Unknown")
        amount = fields.get("amount_due", "?")

        # Escalation: If bill is overdue, add To-do and trigger alert
        if bill and bill.due_date < date.today():
            from app.models.enums import TodoCategory, TodoSource
            from app.models.todo import Todo
            from app.services.push_notification_service import (
                notify_overdue_bill,
            )

            # 1. Add immediate To-do
            todo = Todo(
                user_id=user_id,
                title=f"Pay {sender} bill (${amount})",
                description=f"This bill was due on {bill.due_date}.",
                category=TodoCategory.GENERAL,
                source=TodoSource.DOCUMENT,
            )
            db.add(todo)
            
            # 2. Update bill status to OVERDUE
            from app.models.enums import PaymentStatus
            bill.payment_status = PaymentStatus.OVERDUE
            await db.flush()

            # 3. Notify member & caregivers
            await notify_overdue_bill(db, user_id, sender, str(amount))
            
            logger.info(
                "ESCALATION: Overdue bill from %s triggered To-do and alert",
                sender
            )

        return {
            "success": True,
            "action": "mark_paid" if action == "mark_paid" else "confirmed",
            "record_type": "bill",
            "sender": sender,
            "amount": str(amount),
            "remaining_count": await _get_remaining_count(),
        }

    elif rec_action == RecommendedAction.ADD_APPOINTMENT:
        appt = await create_appointment_from_fields(
            db, user_id, fields,
            source_document_id=review.document_id,
        )
        if appt:
            review.created_record_type = "appointment"
            review.created_record_id = appt.id
        review.review_status = ReviewStatus.CONFIRMED
        review.resolved_at = datetime.utcnow()
        await db.flush()

        provider = fields.get("provider", "your doctor")
        return {
            "success": True,
            "action": "confirmed",
            "record_type": "appointment",
            "provider": provider,
            "remaining_count": await _get_remaining_count(),
        }

    else:
        # file_only, review_with_contact, discard
        review.review_status = ReviewStatus.CONFIRMED
        review.resolved_at = datetime.utcnow()
        await db.flush()
        return {
            "success": True,
            "action": "acknowledged",
            "remaining_count": await _get_remaining_count(),
        }


async def _update_review_fields(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    from app.models.pending_review import PendingReview

    raw_id = str(args.get("review_id", "")).strip()
    updates = args.get("field_updates", {})

    review_id = await _resolve_review_id(
        db, user_id, raw_id
    )
    if review_id is None:
        return {
            "error": True,
            "message": "No pending reviews found.",
        }

    result = await db.execute(
        select(PendingReview).where(
            PendingReview.id == review_id,
            PendingReview.user_id == user_id,
        )
    )
    review = result.scalar_one_or_none()
    if review is None:
        return {"error": True, "message": "Review not found."}

    data = dict(review.proposed_record_data)
    data.update(updates)
    review.proposed_record_data = data
    await db.flush()

    return {
        "success": True,
        "updated_fields": list(updates.keys()),
    }
