"""Shared test configuration.

Reconfigure the database engine for testing to avoid asyncpg event loop
conflicts with httpx ASGITransport. Uses NullPool instead of the default
QueuePool so each request gets a fresh connection.

Also ensures a test user exists so the dev-mode auth bypass works.
When no database is available (local dev without Docker), DB-dependent
tests are skipped but pure unit tests still run.
"""

import asyncio
import os

import pytest
from sqlalchemy import pool, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db import session as db_module

_db_available = False

try:
    # Replace the global engine with a NullPool engine for tests
    _test_engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        poolclass=pool.NullPool,
    )

    _test_session_factory = async_sessionmaker(
        _test_engine,
        expire_on_commit=False,
    )

    # Monkey-patch the db module so the app uses our test engine
    db_module.engine = _test_engine
    db_module.async_session_factory = _test_session_factory

    async def _ensure_test_user():
        """Create a test user if the database is empty."""
        from app.models.user import User

        async with _test_session_factory() as session:
            result = await session.execute(select(User).limit(1))
            existing = result.scalar_one_or_none()
            if existing and not existing.first_name:
                existing.first_name = "Test"
                existing.last_name = "User"
                await session.commit()
            if existing is None:
                user = User(
                    email="test@companion.app",
                    first_name="Test",
                    last_name="User",
                    preferred_name="Test",
                    display_name="Test User",
                    primary_language="en",
                    voice_id="warm",
                    pace_setting="normal",
                    warmth_level="warm",
                )
                session.add(user)
                await session.commit()

    asyncio.get_event_loop().run_until_complete(_ensure_test_user())
    _db_available = True
except Exception as e:
    import warnings

    warnings.warn(
        f"Database not available, DB-dependent tests will be skipped: {e}",
        stacklevel=1,
    )


@pytest.fixture
def db_session():
    """Provide a database session, skip if DB unavailable."""
    if not _db_available:
        pytest.skip("Database not available")

    async def _get_session():
        async with _test_session_factory() as session:
            yield session

    return _get_session


requires_db = pytest.mark.skipif(
    not _db_available, reason="Database not available"
)
