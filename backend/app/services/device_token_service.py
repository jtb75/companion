"""Service layer for FCM device token management."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_token import DeviceToken


async def register_token(
    db: AsyncSession,
    user_id: UUID,
    fcm_token: str,
    platform: str,
    device_name: str | None = None,
) -> DeviceToken:
    """Register or update an FCM device token.

    If the token already exists for a different user, reassign it.
    If it exists for the same user, update last_used_at.
    """
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.fcm_token == fcm_token)
    )
    existing = result.scalar_one_or_none()
    now = datetime.utcnow()

    if existing:
        existing.user_id = user_id
        existing.device_platform = platform
        existing.device_name = device_name
        existing.is_active = True
        existing.last_used_at = now
        await db.flush()
        return existing

    token = DeviceToken(
        user_id=user_id,
        fcm_token=fcm_token,
        device_platform=platform,
        device_name=device_name,
        is_active=True,
        last_used_at=now,
    )
    db.add(token)
    await db.flush()
    return token


async def deactivate_token(
    db: AsyncSession,
    user_id: UUID,
    fcm_token: str,
) -> bool:
    """Deactivate a specific FCM token for a user.

    Returns True if a token was found and deactivated.
    """
    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.user_id == user_id,
            DeviceToken.fcm_token == fcm_token,
        )
    )
    token = result.scalar_one_or_none()
    if token is None:
        return False

    token.is_active = False
    await db.flush()
    return True


async def deactivate_all_tokens(
    db: AsyncSession,
    user_id: UUID,
) -> int:
    """Deactivate all FCM tokens for a user.

    Returns the number of tokens deactivated.
    """
    result = await db.execute(
        update(DeviceToken)
        .where(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active.is_(True),
        )
        .values(is_active=False)
    )
    await db.flush()
    return result.rowcount


async def get_active_tokens(
    db: AsyncSession,
    user_id: UUID,
) -> list[str]:
    """Return active FCM token strings for a user."""
    result = await db.execute(
        select(DeviceToken.fcm_token).where(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active.is_(True),
        )
    )
    return list(result.scalars().all())
