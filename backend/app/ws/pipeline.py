"""WebSocket endpoint for real-time pipeline updates."""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.auth.firebase import verify_firebase_token
from app.pipeline.events import subscribe, unsubscribe

logger = logging.getLogger(__name__)

CHANNEL = "pipeline:updates"


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


async def pipeline_ws_handler(websocket: WebSocket):
    """Stream pipeline events to admin clients via WebSocket."""
    await websocket.accept()

    # Verify admin auth via query param
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_json(
            {"error": "Missing token query parameter"}
        )
        await websocket.close(code=1008)
        return

    try:
        await verify_firebase_token(token)
    except ValueError as exc:
        await websocket.send_json({"error": str(exc)})
        await websocket.close(code=1008)
        return

    if _redis_available():
        await _redis_subscriber(websocket)
    else:
        await _memory_subscriber(websocket)


async def _redis_subscriber(websocket: WebSocket):
    """Subscribe to Redis pub/sub and forward events."""
    from app.db.redis import get_redis

    r = get_redis()
    pubsub = r.pubsub()
    try:
        await pubsub.subscribe(CHANNEL)
        logger.info("WebSocket client subscribed to Redis %s", CHANNEL)

        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await websocket.send_text(msg["data"])
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("WebSocket Redis pipeline error")
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.aclose()
        await r.aclose()


async def _memory_subscriber(websocket: WebSocket):
    """Subscribe to in-process event queue."""
    queue = subscribe()
    logger.info("WebSocket client subscribed to in-process events")
    try:
        while True:
            try:
                event_json = await asyncio.wait_for(
                    queue.get(), timeout=1.0
                )
                await websocket.send_text(event_json)
            except TimeoutError:
                # Keep alive — check if client is still connected
                pass
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("WebSocket memory pipeline error")
    finally:
        unsubscribe(queue)
