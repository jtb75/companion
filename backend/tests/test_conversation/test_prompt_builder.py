"""Unit tests for conversation/prompt_builder.py."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.persona import DD_PERSONA, DEFAULT_CONSTRAINTS
from app.conversation.prompt_builder import build_system_prompt
from app.models.user import User
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


async def test_system_prompt_contains_constitution(db: AsyncSession, user: User):
    """The system prompt must include the D.D. persona (the 'constitution')."""
    prompt = await build_system_prompt(db, user)

    # The persona should be embedded verbatim at the start
    assert DD_PERSONA in prompt
    # Verify key constitutional phrases are present
    assert "Patient, warm, and genuinely caring" in prompt
    assert "Plain language always" in prompt


async def test_system_prompt_includes_user_context(db: AsyncSession, user: User):
    """The prompt must include user-specific context like their name."""
    prompt = await build_system_prompt(db, user)

    name = user.nickname or user.preferred_name
    assert name in prompt
    assert "User Context" in prompt


async def test_system_prompt_includes_constraints(db: AsyncSession, user: User):
    """The prompt must end with the response constraints section."""
    prompt = await build_system_prompt(db, user)

    assert DEFAULT_CONSTRAINTS in prompt
    assert "Response Rules" in prompt
    # Key constraint phrases
    assert "Keep responses under 3 sentences" in prompt
    assert "Tool use rules" in prompt
