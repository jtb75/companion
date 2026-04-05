"""Unit tests for conversation/tool_executor.py handlers."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from app.conversation.tool_executor import execute_tool


def _mock_db_with_scalars(results):
    """Create a mock DB that returns given results from scalars().all()."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = results
    mock_result.scalar_one_or_none.return_value = (
        results[0] if results else None
    )
    db.execute.return_value = mock_result
    db.get.return_value = None
    return db


def _make_med():
    med = MagicMock()
    med.id = uuid.uuid4()
    med.name = "Lisinopril"
    med.dosage = "10mg"
    med.frequency = "once daily"
    med.schedule = ["08:00"]
    med.is_active = True
    med.pharmacy = "Walgreens"
    med.prescriber = "Dr. Smith"
    return med


def _make_bill():
    from datetime import date
    from decimal import Decimal

    bill = MagicMock()
    bill.id = uuid.uuid4()
    bill.sender = "Ameren"
    bill.amount = Decimal("45.00")
    bill.due_date = date(2026, 4, 15)
    bill.payment_status = MagicMock()
    bill.payment_status.value = "pending"
    bill.account_number_masked = "****1234"
    return bill


async def test_list_medications_returns_correct_format():
    """list_medications should return medication data."""
    med = _make_med()
    db = _mock_db_with_scalars([med])
    user_id = uuid.uuid4()

    result = await execute_tool(
        "list_medications", {}, db, user_id
    )

    assert "medications" in result
    assert len(result["medications"]) == 1
    assert result["medications"][0]["name"] == "Lisinopril"


async def test_list_bills_returns_correct_format():
    """list_bills should return bill data."""
    bill = _make_bill()
    db = _mock_db_with_scalars([bill])
    user_id = uuid.uuid4()

    result = await execute_tool(
        "list_bills", {}, db, user_id
    )

    assert "bills" in result
    assert len(result["bills"]) == 1
    assert result["bills"][0]["sender"] == "Ameren"


async def test_unknown_tool_returns_error():
    """An unrecognized tool name should return an error."""
    db = AsyncMock()
    user_id = uuid.uuid4()

    result = await execute_tool(
        "nonexistent_tool", {}, db, user_id
    )

    assert "error" in result or "unknown" in str(result).lower()
