import json

import redis.asyncio as redis

from app.config import settings

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url, decode_responses=True
        )
    return _pool


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_get_pool())


# ── Namespace helpers ────────────────────────────────────────────────────────

CONTEXTUAL_MEMORY_TTL = 48 * 3600  # 48 hours
SESSION_TTL = 2 * 3600             # 2 hours
SECTION_CACHE_TTL = 5 * 60         # 5 minutes
PIPELINE_LOCK_TTL = 10 * 60        # 10 minutes
CONFIG_CACHE_TTL = 5 * 60          # 5 minutes


def ctx_key(user_id: str, memory_id: str) -> str:
    return f"ctx:{user_id}:{memory_id}"


def session_key(user_id: str, session_id: str) -> str:
    return f"session:{user_id}:{session_id}"


def rate_key(api_surface: str, user_id: str) -> str:
    return f"rate:{api_surface}:{user_id}"


def section_cache_key(user_id: str, section: str) -> str:
    return f"cache:section:{user_id}:{section}"


def pipeline_lock_key(document_id: str) -> str:
    return f"lock:pipeline:{document_id}"


def config_cache_key(category: str, key: str) -> str:
    return f"config:{category}:{key}"


async def cache_get(r: redis.Redis, key: str) -> dict | None:
    raw = await r.get(key)
    return json.loads(raw) if raw else None


async def cache_set(r: redis.Redis, key: str, value: dict, ttl: int) -> None:
    await r.set(key, json.dumps(value), ex=ttl)
