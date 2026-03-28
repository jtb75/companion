"""Shared test configuration.

Reconfigure the database engine for testing to avoid asyncpg event loop
conflicts with httpx ASGITransport. Uses NullPool instead of the default
QueuePool so each request gets a fresh connection.
"""

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db import session as db_module

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
