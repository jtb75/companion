"""Shared test configuration.

Reconfigure the database engine for testing to avoid asyncpg event loop
conflicts with httpx ASGITransport. Uses NullPool instead of the default
QueuePool so each request gets a fresh connection.

Also ensures a test user exists so the dev-mode auth bypass works.
"""

import asyncio

from sqlalchemy import pool, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db import session as db_module
from app.models.user import User

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
    """Create a test user if the database is empty (e.g., fresh CI database)."""
    async with _test_session_factory() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            user = User(
                email="test@companion.app",
                preferred_name="Test",
                display_name="Test User",
                primary_language="en",
                voice_id="warm",
                pace_setting="normal",
                warmth_level="warm",
            )
            session.add(user)
            await session.commit()


# Run at import time to ensure user exists before any tests
asyncio.get_event_loop().run_until_complete(_ensure_test_user())
