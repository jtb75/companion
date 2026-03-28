from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bill import Bill
from app.models.enums import PaymentStatus


async def list_bills(
    db: AsyncSession,
    user_id: UUID,
    status: str | None = None,
    due_after: date | None = None,
    due_before: date | None = None,
) -> list[Bill]:
    stmt = select(Bill).where(Bill.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Bill.payment_status == status)
    if due_after is not None:
        stmt = stmt.where(Bill.due_date >= due_after)
    if due_before is not None:
        stmt = stmt.where(Bill.due_date <= due_before)
    stmt = stmt.order_by(Bill.due_date)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_bill(
    db: AsyncSession, user_id: UUID, bill_id: UUID
) -> Bill | None:
    result = await db.execute(
        select(Bill).where(Bill.id == bill_id, Bill.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_bill(db: AsyncSession, user_id: UUID, data: dict) -> Bill:
    bill = Bill(user_id=user_id, **data)
    db.add(bill)
    await db.flush()
    return bill


async def update_bill(
    db: AsyncSession, user_id: UUID, bill_id: UUID, data: dict
) -> Bill | None:
    bill = await get_bill(db, user_id, bill_id)
    if bill is None:
        return None
    for key, value in data.items():
        setattr(bill, key, value)
    await db.flush()
    return bill


async def get_bill_summary(db: AsyncSession, user_id: UUID) -> dict:
    today = date.today()
    end_of_week = today + timedelta(days=7)

    unpaid_statuses = [PaymentStatus.PENDING, PaymentStatus.ACKNOWLEDGED]

    # Total due
    total_result = await db.execute(
        select(func.coalesce(func.sum(Bill.amount), Decimal("0")))
        .where(
            Bill.user_id == user_id,
            Bill.payment_status.in_(unpaid_statuses),
        )
    )
    total_due = total_result.scalar_one()

    # Upcoming count (due today or later, not paid)
    upcoming_result = await db.execute(
        select(func.count())
        .select_from(Bill)
        .where(
            Bill.user_id == user_id,
            Bill.payment_status.in_(unpaid_statuses),
            Bill.due_date >= today,
        )
    )
    upcoming_count = upcoming_result.scalar_one()

    # Overdue count
    overdue_result = await db.execute(
        select(func.count())
        .select_from(Bill)
        .where(
            Bill.user_id == user_id,
            Bill.payment_status.in_([PaymentStatus.PENDING, PaymentStatus.OVERDUE]),
            Bill.due_date < today,
        )
    )
    overdue_count = overdue_result.scalar_one()

    # Bills due this week
    week_result = await db.execute(
        select(Bill)
        .where(
            Bill.user_id == user_id,
            Bill.payment_status.in_(unpaid_statuses),
            Bill.due_date >= today,
            Bill.due_date <= end_of_week,
        )
        .order_by(Bill.due_date)
    )
    bills_due_this_week = list(week_result.scalars().all())

    return {
        "total_due": total_due,
        "upcoming_count": upcoming_count,
        "overdue_count": overdue_count,
        "bills_due_this_week": bills_due_this_week,
    }
