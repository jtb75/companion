"""Unit tests for conversation/tool_executor.py handlers."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.tool_executor import execute_tool
from app.models.enums import ReviewStatus
from app.models.todo import Todo
from app.models.user import User
from tests.utils import make_bill, make_medication, make_todo, make_user

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def db():
    """Provide a database session that rolls back after each test."""
    from tests.conftest import _test_session_factory

    async with _test_session_factory() as session:
        async with session.begin():
            yield session
        # Rollback happens automatically when begin() context exits
        # without commit.


@pytest.fixture
async def user(db: AsyncSession) -> User:
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if user is None:
        user = make_user()
        db.add(user)
        await db.flush()
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_list_medications_returns_correct_format(db: AsyncSession, user: User):
    """list_medications should return a dict with 'medications' list of dicts."""
    med = make_medication(user.id, name="Metformin", dosage="500mg", frequency="twice daily")
    db.add(med)
    await db.flush()

    result = await execute_tool("list_medications", {}, db, user.id)

    assert "medications" in result
    assert isinstance(result["medications"], list)
    assert len(result["medications"]) >= 1

    found = next((m for m in result["medications"] if m["name"] == "Metformin"), None)
    assert found is not None
    assert found["dosage"] == "500mg"
    assert found["frequency"] == "twice daily"
    assert "id" in found


async def test_list_bills_returns_correct_format(db: AsyncSession, user: User):
    """list_bills should return bills ordered by due_date."""
    bill = make_bill(user.id, sender="Water Utility", amount=Decimal("55.00"))
    db.add(bill)
    await db.flush()

    result = await execute_tool("list_bills", {}, db, user.id)

    assert "bills" in result
    assert isinstance(result["bills"], list)
    assert len(result["bills"]) >= 1

    found = next((b for b in result["bills"] if b["sender"] == "Water Utility"), None)
    assert found is not None
    assert found["amount"] == "55.00"
    assert "due_date" in found
    assert "status" in found


async def test_add_todo_creates_a_todo(db: AsyncSession, user: User):
    """add_todo should persist a new Todo and return success."""
    result = await execute_tool(
        "add_todo",
        {"title": "Pick up prescription", "category": "errand"},
        db,
        user.id,
    )

    assert result["success"] is True
    assert result["title"] == "Pick up prescription"
    assert "id" in result

    # Verify the todo was actually created in the DB
    todo_id = uuid.UUID(result["id"])
    row = await db.get(Todo, todo_id)
    assert row is not None
    assert row.title == "Pick up prescription"
    assert row.user_id == user.id


async def test_complete_todo_marks_todo_complete(db: AsyncSession, user: User):
    """complete_todo should set completed_at and is_active=False."""
    todo = make_todo(user.id, title="Wash dishes")
    db.add(todo)
    await db.flush()

    result = await execute_tool(
        "complete_todo",
        {"todo_id": str(todo.id)},
        db,
        user.id,
    )

    assert result["success"] is True
    assert result["title"] == "Wash dishes"

    await db.refresh(todo)
    assert todo.completed_at is not None
    assert todo.is_active is False


async def test_complete_todo_not_found(db: AsyncSession, user: User):
    """complete_todo should return error for nonexistent todo."""
    fake_id = str(uuid.uuid4())
    result = await execute_tool(
        "complete_todo",
        {"todo_id": fake_id},
        db,
        user.id,
    )

    assert result["error"] is True
    assert "not found" in result["message"].lower()


async def test_unknown_tool_returns_error(db: AsyncSession, user: User):
    """An unknown function_name should return an error dict."""
    result = await execute_tool("nonexistent_tool", {}, db, user.id)

    assert result["error"] is True
    assert "Unknown tool" in result["message"]


async def test_get_pending_reviews_returns_reviews(db: AsyncSession, user: User):
    """get_pending_reviews should return reviews with confidence scores."""
    from app.models.pending_review import PendingReview

    review = PendingReview(
        id=uuid.uuid4(),
        user_id=user.id,
        source_description="email from Electric Co",
        recommended_action="add_bill",
        proposed_record_data={"sender": "Electric Co", "amount_due": "120.00"},
        confidence_score=Decimal("0.92"),
        review_status=ReviewStatus.PENDING,
        is_urgent=False,
    )
    db.add(review)
    await db.flush()

    result = await execute_tool("get_pending_reviews", {}, db, user.id)

    assert "reviews" in result
    assert result["count"] >= 1

    found = next(
        (r for r in result["reviews"] if r["source"] == "email from Electric Co"),
        None,
    )
    assert found is not None
    assert found["confidence"] == pytest.approx(0.92, abs=0.01)
    assert found["recommended_action"] == "add_bill"
