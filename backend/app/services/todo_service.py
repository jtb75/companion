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

    # If this is a bill payment todo, mark the bill as paid
    await _sync_bill_payment(db, user_id, todo)

    return todo


async def _sync_bill_payment(
    db: AsyncSession, user_id: UUID, todo: Todo
) -> None:
    """If a completed todo is a bill payment, mark the bill paid."""
    import re

    from app.models.bill import Bill
    from app.models.enums import PaymentStatus

    title = todo.title or ""
    # Match "Pay {sender} bill" pattern
    match = re.match(r"Pay (.+?) bill", title)
    if not match:
        return

    sender = match.group(1)
    result = await db.execute(
        select(Bill).where(
            Bill.user_id == user_id,
            Bill.sender == sender,
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
