"""Shared test utilities: mock LLM client, factories, and helpers."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from app.models.appointment import Appointment
from app.models.bill import Bill
from app.models.enums import (
    PaymentStatus,
    TodoCategory,
    TodoSource,
)
from app.models.medication import Medication
from app.models.todo import Todo
from app.models.user import User

# ---------------------------------------------------------------------------
# Mock LLM client
# ---------------------------------------------------------------------------


class MockLLMClient:
    """A deterministic LLM client for tests.

    By default returns a simple JSON classification. Override ``response``
    or ``response_fn`` for custom behavior.
    """

    def __init__(
        self,
        response: str = '{"classification": "bill", "urgency": "routine", "confidence": 0.9}',
        response_fn=None,
    ):
        self.response = response
        self.response_fn = response_fn
        self.calls: list[dict] = []

    async def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 500,
        **kwargs,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "messages": messages,
                "max_tokens": max_tokens,
                **kwargs,
            }
        )
        if self.response_fn:
            return self.response_fn(system_prompt, messages)
        return self.response

    async def generate_stream(self, system_prompt, messages, **kwargs):
        text = await self.generate(system_prompt, messages, **kwargs)
        yield text


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def make_user(
    *,
    email: str = "test@companion.app",
    preferred_name: str = "Test",
    display_name: str = "Test User",
    first_name: str = "Test",
    last_name: str = "User",
    user_id: uuid.UUID | None = None,
) -> User:
    """Build a User instance (not yet added to a session)."""
    user = User(
        id=user_id or uuid.uuid4(),
        email=email,
        preferred_name=preferred_name,
        display_name=display_name,
        first_name=first_name,
        last_name=last_name,
        primary_language="en",
        voice_id="warm",
        pace_setting="normal",
        warmth_level="warm",
    )
    return user


def make_medication(
    user_id: uuid.UUID,
    *,
    name: str = "Lisinopril",
    dosage: str = "10mg",
    frequency: str = "daily",
    is_active: bool = True,
) -> Medication:
    return Medication(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        dosage=dosage,
        frequency=frequency,
        schedule={"times": ["08:00"]},
        is_active=is_active,
    )


def make_bill(
    user_id: uuid.UUID,
    *,
    sender: str = "Electric Co",
    amount: Decimal = Decimal("120.00"),
    due_date: date | None = None,
    payment_status: PaymentStatus = PaymentStatus.PENDING,
) -> Bill:
    return Bill(
        id=uuid.uuid4(),
        user_id=user_id,
        sender=sender,
        amount=amount,
        due_date=due_date or date.today(),
        payment_status=payment_status,
    )


def make_todo(
    user_id: uuid.UUID,
    *,
    title: str = "Buy groceries",
    category: TodoCategory = TodoCategory.GENERAL,
    source: TodoSource = TodoSource.USER,
    due_date: date | None = None,
    related_bill_id: uuid.UUID | None = None,
) -> Todo:
    return Todo(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title,
        category=category,
        source=source,
        due_date=due_date,
        is_active=True,
        related_bill_id=related_bill_id,
    )


def make_appointment(
    user_id: uuid.UUID,
    *,
    provider_name: str = "Dr. Smith",
    appointment_at: datetime | None = None,
    preparation_notes: str | None = None,
) -> Appointment:
    return Appointment(
        id=uuid.uuid4(),
        user_id=user_id,
        provider_name=provider_name,
        appointment_at=appointment_at or datetime(2026, 5, 1, 10, 0),
        preparation_notes=preparation_notes,
    )


# ---------------------------------------------------------------------------
# Authenticated test client helper
# ---------------------------------------------------------------------------


def get_authenticated_client(app, user: User | None = None):
    """Return an httpx.AsyncClient wired to the app.

    When dev_auth_bypass is True the app auto-resolves the first DB user,
    so no Authorization header is needed. This helper exists for clarity
    and future-proofing.
    """
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")
