from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.todo import Todo


async def list_todos(
    db: AsyncSession, user_id: UUID, active_only: bool = True
) -> list[Todo]:
    stmt = select(Todo).where(Todo.user_id == user_id)
    if active_only:
        stmt = stmt.where(Todo.is_active.is_(True))
    stmt = stmt.order_by(Todo.due_date.asc().nulls_last(), Todo.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_todo(db: AsyncSession, user_id: UUID, data: dict) -> Todo:
    todo = Todo(user_id=user_id, **data)
    db.add(todo)
    await db.flush()
    return todo


async def update_todo(
    db: AsyncSession, user_id: UUID, todo_id: UUID, data: dict
) -> Todo | None:
    result = await db.execute(
        select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        return None
    for key, value in data.items():
        setattr(todo, key, value)
    await db.flush()
    return todo


async def delete_todo(
    db: AsyncSession, user_id: UUID, todo_id: UUID
) -> bool:
    result = await db.execute(
        select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        return False
    todo.is_active = False
    await db.flush()
    return True


async def complete_todo(
    db: AsyncSession, user_id: UUID, todo_id: UUID
) -> Todo | None:
    result = await db.execute(
        select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
    )
    todo = result.scalar_one_or_none()
    if todo is None:
        return None
    todo.completed_at = datetime.utcnow()
    todo.is_active = False
    await db.flush()

    # If this todo is linked to a bill, mark it paid
    await _sync_bill_on_complete(db, user_id, todo)

    return todo


async def _sync_bill_on_complete(
    db: AsyncSession, user_id: UUID, todo: Todo
) -> None:
    """Mark the associated bill as paid when a bill todo completes."""
    import re

    from app.models.bill import Bill
    from app.models.enums import PaymentStatus

    # Prefer explicit FK link
    if todo.related_bill_id:
        bill = await db.get(Bill, todo.related_bill_id)
        if bill and bill.payment_status in (
            PaymentStatus.PENDING,
            PaymentStatus.OVERDUE,
        ):
            bill.payment_status = PaymentStatus.PAID
            await db.flush()
        return

    # Fallback: match "Pay {sender} bill" title pattern
    # for legacy todos created before related_bill_id existed
    title = todo.title or ""
    match = re.match(r"Pay (.+?) bill", title, re.IGNORECASE)
    if not match:
        return

    sender = match.group(1).strip()
    result = await db.execute(
        select(Bill)
        .where(
            Bill.user_id == user_id,
            Bill.sender.ilike(f"%{sender}%"),
            Bill.payment_status.in_([
                PaymentStatus.PENDING,
                PaymentStatus.OVERDUE,
            ]),
        )
        .order_by(Bill.due_date.desc())
        .limit(1)
    )
    bill = result.scalar_one_or_none()
    if bill:
        bill.payment_status = PaymentStatus.PAID
        await db.flush()
