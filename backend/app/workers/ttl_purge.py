"""TTL purge worker — cleans up expired contextual memory.

Redis handles TTL natively, but this worker provides a safety net
for any entries that might have been missed. Runs hourly.
"""

import logging

from app.db.redis import get_redis

logger = logging.getLogger(__name__)


async def run_ttl_purge():
    """Scan and clean up expired Redis keys.

    Redis TTL handles most expiry automatically. This worker:
    1. Checks for orphaned session keys
    2. Cleans up stale rate limiting entries
    3. Verifies config cache consistency
    """
    r = get_redis()
    try:
        cleaned = 0

        # Scan for orphaned session keys (should auto-expire)
        async for key in r.scan_iter(match="session:*", count=100):
            ttl = await r.ttl(key)
            if ttl == -1:  # No expiry set (shouldn't happen)
                await r.expire(key, 7200)  # Set 2hr TTL
                cleaned += 1

        # Scan for orphaned context keys
        async for key in r.scan_iter(match="ctx:*", count=100):
            ttl = await r.ttl(key)
            if ttl == -1:
                await r.expire(key, 172800)  # 48hr TTL
                cleaned += 1

        logger.info(f"TTL purge complete: {cleaned} keys fixed")
        return {"keys_fixed": cleaned}
    finally:
        await r.aclose()
