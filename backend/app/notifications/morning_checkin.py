from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.bill import Bill
from app.models.enums import PaymentStatus
from app.models.medication import Medication, MedicationConfirmation
from app.notifications.priority import (
    NotificationItem,
    assign_priority,
    priority_label,
)

logger = logging.getLogger(__name__)

DAYS_OF_WEEK = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]


async def assemble_morning_checkin(
    db: AsyncSession, user_id: UUID, user_name: str
) -> dict:
    """Assemble the morning check-in content.

    Returns a structured dict with sections that can be
    rendered as text or passed to the LLM for spoken delivery.
    """
    today = date.today()
    day_name = DAYS_OF_WEEK[today.weekday()]
    week_end = today + timedelta(days=7)

    items = []

    # Gather bills: overdue always, pending/acknowledged within 7 days
    from sqlalchemy import or_

    result = await db.execute(
        select(Bill).where(
            Bill.user_id == user_id,
            or_(
                Bill.payment_status == PaymentStatus.OVERDUE,
                Bill.payment_status.in_([
                    PaymentStatus.PENDING,
                    PaymentStatus.ACKNOWLEDGED,
                ]) & (Bill.due_date <= week_end),
            ),
        ).order_by(Bill.due_date)
    )
    for bill in result.scalars().all():
        items.append(NotificationItem(
            id=bill.id,
            user_id=user_id,
            item_type="bill",
            title=f"{bill.sender}",
            detail=f"${bill.amount} due {bill.due_date}",
            relevant_date=bill.due_date,
        ))

    # Gather appointments this week
    datetime.combine(
        today + timedelta(days=1), datetime.min.time()
    )
    week_end_dt = datetime.combine(week_end, datetime.min.time())

    result = await db.execute(
        select(Appointment).where(
            Appointment.user_id == user_id,
            Appointment.appointment_at >= datetime.combine(
                today, datetime.min.time()
            ),
            Appointment.appointment_at < week_end_dt,
        ).order_by(Appointment.appointment_at)
    )
    for appt in result.scalars().all():
        appt_date = appt.appointment_at.date() if hasattr(
            appt.appointment_at, 'date'
        ) else today
        items.append(NotificationItem(
            id=appt.id,
            user_id=user_id,
            item_type="appointment",
            title=appt.provider_name,
            detail=str(appt.appointment_at),
            relevant_date=appt_date,
        ))

    # Gather medications (check if confirmed today)
    result = await db.execute(
        select(Medication).where(
            Medication.user_id == user_id,
            Medication.is_active.is_(True),
        )
    )
    for med in result.scalars().all():
        # Check if already confirmed today
        conf_result = await db.execute(
            select(MedicationConfirmation).where(
                MedicationConfirmation.medication_id == med.id,
                MedicationConfirmation.confirmed_at.isnot(None),
                MedicationConfirmation.scheduled_at >= datetime.combine(
                    today, datetime.min.time()
                ),
            ).limit(1)
        )
        confirmed_today = conf_result.scalar_one_or_none() is not None

        if not confirmed_today:
            items.append(NotificationItem(
                id=med.id,
                user_id=user_id,
                item_type="medication",
                title=f"Take {med.name} ({med.dosage})",
                detail=med.frequency,
                relevant_date=today,
                category="missed" if datetime.utcnow().hour > 12 else "",
            ))

    # Gather active todos (due soon or no due date)
    from app.models.todo import Todo

    result = await db.execute(
        select(Todo).where(
            Todo.user_id == user_id,
            Todo.is_active.is_(True),
            Todo.completed_at.is_(None),
        ).order_by(Todo.due_date.asc().nullslast())
        .limit(5)
    )
    for todo in result.scalars().all():
        due = todo.due_date
        # Include if due within 7 days or no due date
        if due is None or due <= week_end:
            items.append(NotificationItem(
                id=todo.id,
                user_id=user_id,
                item_type="todo",
                title=todo.title,
                detail=(
                    f"due {due}" if due else "no due date"
                ),
                relevant_date=due or today,
            ))

    # Assign priorities
    for item in items:
        item.priority_level = assign_priority(item)

    # Sort by priority then date
    items.sort(key=lambda i: (i.priority_level, i.relevant_date or today))

    # Split into sections
    urgent = [i for i in items if i.priority_level <= 2]
    today_items = [
        i for i in items
        if i.priority_level > 2
        and i.relevant_date == today
    ]
    week_items = [
        i for i in items
        if i.priority_level >= 3
        and i.relevant_date
        and i.relevant_date > today
    ]

    # Build text sections
    greeting = f"Good morning, {user_name}. It's {day_name}."

    urgent_text = ""
    if urgent:
        if len(urgent) == 1:
            u = urgent[0]
            urgent_text = f"First — {u.title}. {u.detail}."
        else:
            urgent_text = (
                f"You have {len(urgent)} things that need "
                "attention today. Let's go through them."
            )

    today_text = ""
    if today_items:
        parts = [f"{i.title}" for i in today_items[:3]]
        today_text = "Today: " + ", ".join(parts) + "."

    week_text = ""
    if week_items:
        parts = [
            f"{i.title} ({i.detail})" for i in week_items[:5]
        ]
        week_text = "This week: " + "; ".join(parts) + "."

    close = "That's everything for now. I'm here if you need me."

    return {
        "greeting": greeting,
        "urgent": urgent_text,
        "urgent_items": [
            _item_to_dict(i) for i in urgent
        ],
        "today": today_text,
        "today_items": [
            _item_to_dict(i) for i in today_items
        ],
        "this_week": week_text,
        "week_items": [
            _item_to_dict(i) for i in week_items[:5]
        ],
        "close": close,
        "total_items": len(items),
        "urgent_count": len(urgent),
    }


def _item_to_dict(item: NotificationItem) -> dict:
    return {
        "id": str(item.id),
        "type": item.item_type,
        "title": item.title,
        "detail": item.detail,
        "priority": item.priority_level,
        "label": priority_label(item.priority_level),
    }
