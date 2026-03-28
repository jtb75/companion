from __future__ import annotations

import logging
from uuid import UUID

from app.events.publisher import event_publisher
from app.events.schemas import NotificationDeliveredPayload

logger = logging.getLogger(__name__)


async def deliver_push(
    user_id: UUID, title: str, body: str, data: dict | None = None
) -> bool:
    """Send a push notification via Firebase Cloud Messaging.

    Stubbed for now — will integrate with Firebase Admin SDK.
    """
    logger.info(
        f"Push notification: user={user_id} "
        f"title=\"{title}\" body=\"{body[:60]}...\""
    )

    # TODO: Firebase Cloud Messaging integration
    # from firebase_admin import messaging
    # message = messaging.Message(
    #     notification=messaging.Notification(title=title, body=body),
    #     data=data or {},
    #     token=user_fcm_token,
    # )
    # messaging.send(message)

    await event_publisher.publish(
        "notification.delivered",
        user_id=user_id,
        payload=NotificationDeliveredPayload(
            notification_id=UUID(int=0),
            channel="push",
            user_id=user_id,
            content_type="text",
        ),
    )
    return True


async def deliver_in_app(
    user_id: UUID, title: str, body: str, priority: int = 4
) -> bool:
    """Create an in-app notification card.

    In a full implementation, this writes to a notifications table
    and the mobile app polls or receives via WebSocket.
    """
    logger.info(
        f"In-app notification: user={user_id} "
        f"priority={priority} title=\"{title}\""
    )
    # TODO: Write to notifications table
    return True


async def deliver_voice(
    user_id: UUID, text: str, voice_id: str = "warm"
) -> bool:
    """Queue a voice notification for Arlo to speak.

    Used when the app is open and active.
    """
    logger.info(
        f"Voice notification: user={user_id} "
        f"voice={voice_id} text=\"{text[:60]}...\""
    )
    # TODO: Queue for TTS delivery via conversation layer
    return True
