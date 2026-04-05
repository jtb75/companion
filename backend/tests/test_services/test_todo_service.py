"""Unit tests for services/todo_service.py."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentStatus, TodoCategory
from app.models.user import User
from app.services.todo_service import complete_todo, create_todo
from tests.utils import make_bill, make_todo, make_user


@pytest.fixture
async def db():
    from tests.conftest import _test_session_factory

    async with _test_session_factory() as session:
        async with session.begin():
            yield session


@pytest.fixture
async def user(db: AsyncSession) -> User:
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if user is None:
        user = make_user()
        db.add(user)
        await db.flush()
    return user


async def test_create_todo(db: AsyncSession, user: User):
    """create_todo should persist a new Todo and return it."""
    todo = await create_todo(
        db,
        user.id,
        {"title": "Call dentist", "category": TodoCategory.GENERAL},
    )

    assert todo.id is not None
    assert todo.title == "Call dentist"
    assert todo.user_id == user.id
    assert todo.is_active is True
    assert todo.completed_at is None


async def test_complete_todo(db: AsyncSession, user: User):
    """complete_todo should set completed_at and is_active=False."""
    todo = make_todo(user.id, title="Take out trash")
    db.add(todo)
    await db.flush()

    result = await complete_todo(db, user.id, todo.id)

    assert result is not None
    assert result.completed_at is not None
    assert result.is_active is False


async def test_complete_bill_todo_marks_bill_paid(db: AsyncSession, user: User):
    """Completing a todo linked to a bill should mark the bill as paid."""
    bill = make_bill(
        user.id,
        sender="Gas Company",
        amount=Decimal("89.00"),
        payment_status=PaymentStatus.PENDING,
    )
    db.add(bill)
    await db.flush()

    todo = make_todo(
        user.id,
        title="Pay gas bill",
        related_bill_id=bill.id,
    )
    db.add(todo)
    await db.flush()

    result = await complete_todo(db, user.id, todo.id)

    assert result is not None
    assert result.completed_at is not None

    await db.refresh(bill)
    assert bill.payment_status == PaymentStatus.PAID


async def test_complete_non_bill_todo_no_side_effects(db: AsyncSession, user: User):
    """Completing a todo with no related_bill_id should not affect any bills."""
    bill = make_bill(
        user.id,
        sender="Phone Co",
        amount=Decimal("50.00"),
        payment_status=PaymentStatus.PENDING,
    )
    db.add(bill)
    await db.flush()

    todo = make_todo(user.id, title="Walk the dog")
    db.add(todo)
    await db.flush()

    result = await complete_todo(db, user.id, todo.id)

    assert result is not None
    assert result.completed_at is not None

    # Bill should remain PENDING
    await db.refresh(bill)
    assert bill.payment_status == PaymentStatus.PENDING


async def test_complete_nonexistent_todo_returns_none(db: AsyncSession, user: User):
    """complete_todo with a bad ID should return None."""
    result = await complete_todo(db, user.id, uuid.uuid4())
    assert result is None
