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
    await db.flush()
    return {
        "success": True,
        "id": str(appt.id),
        "provider": appt.provider_name,
        "at": appt.appointment_at.isoformat(),
    }


async def _add_todo(
    db: AsyncSession, user_id: UUID, args: dict
) -> dict:
    due = None
    if args.get("due_date"):
        due = date.fromisoformat(args["due_date"])
    todo = Todo(
        user_id=user_id,
        title=args["title"],
        due_date=due,
        category=args.get("category", "general"),
    )
    db.add(todo)
    await db.flush()
    return {
        "success": True,
        "id": str(todo.id),
        "title": todo.title,
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
    }
