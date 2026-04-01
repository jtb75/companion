"""Pipeline event publisher — pushes stage updates to Redis pub/sub."""

import json
import logging
from datetime import UTC, datetime

from app.db.redis import get_redis

logger = logging.getLogger(__name__)

CHANNEL = "pipeline:updates"


async def publish_pipeline_event(
    document_id: str,
    stage: str,
    status: str,
    metadata: dict | None = None,
) -> None:
    """Publish a pipeline stage event to Redis pub/sub.

    Fails gracefully — logs a warning if Redis is unavailable.
    """
    event = {
        "document_id": str(document_id),
        "stage": stage,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if metadata:
        event["metadata"] = metadata

    try:
        r = get_redis()
        await r.publish(CHANNEL, json.dumps(event))
        await r.aclose()
    except Exception:
        logger.warning(
            "Failed to publish pipeline event for doc %s",
            document_id,
            exc_info=True,
        )
