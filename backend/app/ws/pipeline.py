"""WebSocket endpoint for real-time pipeline updates."""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.auth.firebase import verify_firebase_token
from app.db.redis import get_redis

logger = logging.getLogger(__name__)

CHANNEL = "pipeline:updates"


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

    # Subscribe to Redis pub/sub
    r = get_redis()
    pubsub = r.pubsub()
    try:
        await pubsub.subscribe(CHANNEL)
        logger.info("WebSocket client subscribed to %s", CHANNEL)

        while True:
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if msg and msg["type"] == "message":
                await websocket.send_text(msg["data"])
            else:
                # Yield control so disconnect can be detected
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("WebSocket pipeline error")
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.aclose()
        await r.aclose()
