"""Unit tests for services/push_notification_service.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.push_notification_service import (
    notify_document_processed,
    notify_medication_reminder,
    send_push,
)
from tests.utils import make_user


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


async def test_send_push_no_tokens_returns_zero(db: AsyncSession, user: User):
    """send_push should return 0 when the user has no active device tokens."""
    with patch(
        "app.services.push_notification_service.device_token_service"
    ) as mock_dts:
        mock_dts.get_active_tokens = AsyncMock(return_value=[])

        sent = await send_push(db, user.id, "Test Title", "Test Body")

    assert sent == 0


async def test_notify_document_processed_calls_send_push(db: AsyncSession, user: User):
    """notify_document_processed should delegate to send_push with correct args."""
    with patch(
        "app.services.push_notification_service.send_push",
        new_callable=AsyncMock,
        return_value=1,
    ) as mock_send:
        result = await notify_document_processed(
            db, user.id, "Your electric bill is ready."
        )

    assert result == 1
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args
    # Positional args: db, user_id, title, body
    assert call_kwargs[1]["title"] == "Document Ready"
    assert "electric bill" in call_kwargs[1]["body"]
    assert call_kwargs[1]["data"] == {"type": "document_processed"}


async def test_notify_medication_reminder_calls_send_push(db: AsyncSession, user: User):
    """notify_medication_reminder should send a push with the medication name."""
    with patch(
        "app.services.push_notification_service.send_push",
        new_callable=AsyncMock,
        return_value=1,
    ) as mock_send:
        result = await notify_medication_reminder(db, user.id, "Lisinopril")

    assert result == 1
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args
    assert call_kwargs[1]["title"] == "Medication Reminder"
    assert "Lisinopril" in call_kwargs[1]["body"]
