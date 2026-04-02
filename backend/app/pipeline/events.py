"""Pipeline event publisher — pushes stage updates via Redis or in-process."""

import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CHANNEL = "pipeline:updates"

# In-process fallback when Redis is unavailable
_subscribers: set[asyncio.Queue] = set()


def _redis_available() -> bool:
    """Check if Redis is configured and reachable."""
    try:
        from app.config import settings
        url = settings.redis_url
        if not url or "disabled" in url or "localhost" in url:
            return False
        return True
    except Exception:
        return False


async def publish_pipeline_event(
    document_id: str,
    stage: str,
    status: str,
    metadata: dict | None = None,
) -> None:
    """Publish a pipeline stage event.

    Uses Redis pub/sub if available, otherwise broadcasts
    to in-process subscribers (WebSocket handlers).
    """
    event = {
        "document_id": str(document_id),
        "stage": stage,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if metadata:
        event["metadata"] = metadata

    event_json = json.dumps(event)

    if _redis_available():
        try:
            from app.db.redis import get_redis
            r = get_redis()
            listeners = await r.publish(CHANNEL, event_json)
            await r.aclose()
            logger.info(
                "PIPELINE_EVENT[redis]: doc=%s stage=%s "
                "status=%s listeners=%d",
                document_id, stage, status, listeners,
            )
            return
        except Exception:
            logger.warning(
                "Redis publish failed, using in-process",
                exc_info=True,
            )

    # In-process broadcast
    for queue in _subscribers:
        try:
            queue.put_nowait(event_json)
        except asyncio.QueueFull:
            pass
    logger.info(
        "PIPELINE_EVENT[memory]: doc=%s stage=%s "
        "status=%s subs=%d",
        document_id, stage, status, len(_subscribers),
    )


def subscribe() -> asyncio.Queue:
    """Create a new subscriber queue for pipeline events."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(queue)
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    """Remove a subscriber queue."""
    _subscribers.discard(queue)
