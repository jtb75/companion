"""Unit tests for services/push_notification_service.py."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.push_notification_service import (
    notify_document_processed,
    notify_medication_reminder,
    send_push,
)


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def user_id():
    return uuid.uuid4()


async def test_send_push_no_tokens_returns_zero(mock_db, user_id):
    """send_push should return 0 when the user has no active device tokens."""
    with patch(
        "app.services.push_notification_service.device_token_service"
    ) as mock_dts:
        mock_dts.get_active_tokens = AsyncMock(return_value=[])
        sent = await send_push(
            mock_db, user_id, "Test Title", "Test Body"
        )
    assert sent == 0


async def test_notify_document_processed_calls_send_push(
    mock_db, user_id
):
    """notify_document_processed should delegate to send_push."""
    with patch(
        "app.services.push_notification_service.send_push",
        new_callable=AsyncMock,
        return_value=1,
    ) as mock_send:
        result = await notify_document_processed(
            mock_db, user_id, "Your electric bill is ready."
        )
    assert result == 1
    mock_send.assert_called_once()
    _, kwargs = mock_send.call_args
    assert kwargs["title"] == "Document Ready"
    assert "electric bill" in kwargs["body"]


async def test_notify_medication_reminder_calls_send_push(
    mock_db, user_id
):
    """notify_medication_reminder should include the medication name."""
    with patch(
        "app.services.push_notification_service.send_push",
        new_callable=AsyncMock,
        return_value=1,
    ) as mock_send:
        result = await notify_medication_reminder(
            mock_db, user_id, "Lisinopril"
        )
    assert result == 1
    mock_send.assert_called_once()
    _, kwargs = mock_send.call_args
    assert kwargs["title"] == "Medication Reminder"
    assert "Lisinopril" in kwargs["body"]
