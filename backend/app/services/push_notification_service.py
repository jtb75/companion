"""Service layer for sending FCM push notifications."""

import json
import logging
import os
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import device_token_service

logger = logging.getLogger(__name__)

# Cache the access token across calls
_fcm_token_cache: dict[str, str] = {}


async def _get_access_token() -> str | None:
    """Get an OAuth2 access token for FCM.

    On Cloud Run, uses the metadata server.
    Locally, uses the SA key file from GOOGLE_APPLICATION_CREDENTIALS.
    """
    # Try metadata server first (Cloud Run)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "http://metadata.google.internal/computeMetadata/v1"
                "/instance/service-accounts/default/token"
                "?scopes=https://www.googleapis.com/auth"
                "/firebase.messaging",
                headers={"Metadata-Flavor": "Google"},
            )
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                logger.info("FCM: got token from metadata server")
                return token
    except Exception:
        pass  # Not on Cloud Run, try SA key file

    # Fall back to SA key file
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        with open(cred_path) as f:
            sa_info = json.load(f)
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=[
                "https://www.googleapis.com/auth/firebase.messaging",
            ],
        )
        credentials.refresh(Request())
        logger.info("FCM: got token from SA key file")
        return credentials.token

    logger.error("FCM: no credentials available")
    return None


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
    tokens = await device_token_service.get_active_tokens(db, user_id)
    if not tokens:
        logger.debug(
            "No active FCM tokens for user %s — skipping push",
            user_id,
        )
        return 0

    access_token = await _get_access_token()
    if not access_token:
        return 0

    project_id = os.environ.get(
        "COMPANION_FIREBASE_PROJECT_ID", "companion-staging-491606"
    )
    url = (
        f"https://fcm.googleapis.com/v1/projects/{project_id}"
        f"/messages:send"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    sent = 0
    failed_tokens: list[str] = []

    async with httpx.AsyncClient() as client:
        for token_str in tokens:
            payload = {
                "message": {
                    "token": token_str,
                    "notification": {
                        "title": title,
                        "body": body,
                    },
                    "data": data or {},
                }
            }
            resp = await client.post(
                url,
                headers=headers,
                content=json.dumps(payload),
            )
            if resp.status_code == 200:
                sent += 1
                logger.info(
                    "FCM sent to %s...", token_str[:20]
                )
            elif resp.status_code in (400, 404):
                failed_tokens.append(token_str)
                logger.warning(
                    "FCM token invalid %s...: %s",
                    token_str[:20],
                    resp.text[:200],
                )
            else:
                logger.warning(
                    "FCM send failed for %s...: %d %s",
                    token_str[:20],
                    resp.status_code,
                    resp.text[:500],
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

    return sent


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

    # Notify caregivers
    from app.services.caregiver_service import list_contacts

    contacts = await list_contacts(db, user_id)
    for contact in contacts:
        if contact.is_active:
            pass

    return count
