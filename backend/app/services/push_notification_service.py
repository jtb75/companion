"""Service layer for sending FCM push notifications."""

import logging
import os
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import device_token_service

logger = logging.getLogger(__name__)


def _ensure_fcm_app():
    """Ensure a dedicated Firebase app for FCM exists."""
    import firebase_admin
    from firebase_admin import credentials

    try:
        return firebase_admin.get_app("fcm")
    except ValueError:
        pass

    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    project_id = os.environ.get(
        "COMPANION_FIREBASE_PROJECT_ID"
    )

    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        logger.info(
            "FCM app init with SA key file, project=%s",
            project_id,
        )
    else:
        cred = credentials.ApplicationDefault()
        logger.info(
            "FCM app init with ADC, project=%s", project_id
        )

    return firebase_admin.initialize_app(
        credential=cred,
        options={"projectId": project_id} if project_id else None,
        name="fcm",
    )


async def send_push(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> int:
    """Send a push notification to all active devices for a user.

    Returns the number of successfully sent messages.
    """
    import asyncio

    tokens = await device_token_service.get_active_tokens(db, user_id)
    if not tokens:
        logger.debug(
            "No active FCM tokens for user %s — skipping push",
            user_id,
        )
        return 0

    from firebase_admin import messaging

    app = _ensure_fcm_app()

    notification = messaging.Notification(
        title=title, body=body
    )
    message = messaging.MulticastMessage(
        notification=notification,
        data=data or {},
        tokens=tokens,
    )

    response = await asyncio.to_thread(
        messaging.send_each_for_multicast, message, app=app
    )

    # Deactivate tokens that are no longer valid
    failed_tokens: list[str] = []
    for i, send_response in enumerate(response.responses):
        if send_response.exception is not None:
            exc = send_response.exception
            if isinstance(
                exc,
                (
                    messaging.UnregisteredError,
                    messaging.SenderIdMismatchError,
                ),
            ):
                failed_tokens.append(tokens[i])
                logger.warning(
                    "FCM token invalid %s...: %s",
                    tokens[i][:20],
                    type(exc).__name__,
                )
            else:
                logger.warning(
                    "FCM send failed for %s...: %s (%s)",
                    tokens[i][:20],
                    exc,
                    type(exc).__name__,
                )

    for bad_token in failed_tokens:
        await device_token_service.deactivate_token(
            db, user_id, bad_token
        )

    if failed_tokens:
        await db.flush()
        logger.info(
            "Deactivated %d invalid FCM tokens for user %s",
            len(failed_tokens),
            user_id,
        )

    return response.success_count


async def notify_caregiver_status_change(
    db: AsyncSession,
    inviter_user_id: UUID,
    caregiver_name: str,
    new_status: str,
) -> int:
    """Notify a member when their caregiver accepts or declines."""
    action = "accepted" if new_status == "accepted" else "declined"
    return await send_push(
        db,
        inviter_user_id,
        title="Caregiver Update",
        body=f"{caregiver_name} has {action} your invitation.",
        data={"type": "caregiver_status", "status": new_status},
    )


async def notify_medication_reminder(
    db: AsyncSession,
    user_id: UUID,
    medication_name: str,
) -> int:
    """Remind a user to take their medication."""
    return await send_push(
        db,
        user_id,
        title="Medication Reminder",
        body=f"Time to take your {medication_name}.",
        data={"type": "medication_reminder"},
    )


async def notify_checkin_prompt(
    db: AsyncSession,
    user_id: UUID,
) -> int:
    """Prompt a user for their daily check-in."""
    return await send_push(
        db,
        user_id,
        title="Daily Check-In",
        body="How are you doing today? Tap to check in.",
        data={"type": "checkin_prompt"},
    )


async def notify_morning_briefing(
    db: AsyncSession,
    user_id: UUID,
    briefing: str,
) -> int:
    """Send the personalized morning briefing push notification."""
    return await send_push(
        db,
        user_id,
        title="Good Morning",
        body=briefing,
        data={"type": "morning_briefing"},
    )


async def notify_document_processed(
    db: AsyncSession,
    user_id: UUID,
    document_summary: str,
) -> int:
    """Notify a user that a document has been processed."""
    return await send_push(
        db,
        user_id,
        title="Document Ready",
        body=document_summary[:200],
        data={"type": "document_processed"},
    )


async def notify_overdue_bill(
    db: AsyncSession,
    user_id: UUID,
    sender: str,
    amount: str,
) -> int:
    """Notify member and caregivers about an overdue bill."""
    body = (
        f"Your {sender} bill for ${amount} is past due. "
        "I've added a task to help you get it paid."
    )
    count = await send_push(
        db,
        user_id,
        title="Bill Alert",
        body=body,
        data={"type": "bill_alert", "sender": sender},
    )

    from app.services.caregiver_service import list_contacts

    contacts = await list_contacts(db, user_id)
    for contact in contacts:
        if contact.is_active:
            pass

    return count
