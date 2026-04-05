"""Unit tests for services/todo_service.py."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.enums import PaymentStatus
from app.services.todo_service import complete_todo


def _mock_db():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    db.get.return_value = None
    db.flush = AsyncMock()
    return db


def _make_todo(user_id, title="Test todo", bill_id=None):
    todo = MagicMock()
    todo.id = uuid.uuid4()
    todo.user_id = user_id
    todo.title = title
    todo.completed_at = None
    todo.is_active = True
    todo.related_bill_id = bill_id
    return todo


async def test_complete_todo_returns_none_for_missing():
    """complete_todo returns None if the todo doesn't exist."""
    db = _mock_db()
    result = await complete_todo(db, uuid.uuid4(), uuid.uuid4())
    assert result is None


async def test_complete_todo_sets_completed_at():
    """complete_todo should set completed_at and is_active=False."""
    user_id = uuid.uuid4()
    todo = _make_todo(user_id)

    db = _mock_db()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = todo
    db.execute.return_value = mock_result

    result = await complete_todo(db, user_id, todo.id)

    assert result is not None
    assert todo.completed_at is not None
    assert todo.is_active is False


async def test_complete_bill_todo_marks_bill_paid():
    """Completing a todo linked to a bill marks the bill paid."""
    user_id = uuid.uuid4()
    bill_id = uuid.uuid4()
    todo = _make_todo(
        user_id, title="Pay Ameren bill ($45)", bill_id=bill_id
    )

    bill = MagicMock()
    bill.payment_status = PaymentStatus.PENDING

    db = _mock_db()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = todo
    db.execute.return_value = mock_result
    db.get.return_value = bill

    await complete_todo(db, user_id, todo.id)

    assert bill.payment_status == PaymentStatus.PAID


async def test_complete_non_bill_todo_no_side_effects():
    """Completing a todo without related_bill_id doesn't touch bills."""
    user_id = uuid.uuid4()
    todo = _make_todo(user_id, title="Buy groceries")

    db = _mock_db()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = todo
    db.execute.return_value = mock_result

    await complete_todo(db, user_id, todo.id)

    db.get.assert_not_called()
