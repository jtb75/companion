"""App API — Notification routes.

Stub — notification delivery involves external services not in Phase 3.
Service calls will be wired when notification_service is implemented.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, get_current_user
from app.db import get_db

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications."""
    return {
        "notifications": [],
        "total": 0,
        "unread_count": 0,
    }


@router.patch("/{notification_id}")
async def acknowledge_notification(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss or acknowledge a notification."""
    return {
        "id": str(notification_id),
        "acknowledged": True,
    }


@router.get("/preferences")
async def get_notification_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification preferences."""
    return {
        "push_enabled": True,
        "email_enabled": False,
        "quiet_hours": {"start": "22:00", "end": "07:00"},
        "categories": {},
    }


@router.patch("/preferences")
async def update_notification_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification preferences."""
    return {
        "push_enabled": True,
        "email_enabled": False,
        "quiet_hours": {"start": "22:00", "end": "07:00"},
        "categories": {},
        "updated": True,
    }
