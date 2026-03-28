"""App API — Notification routes."""

import uuid

from fastapi import APIRouter, Depends

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(user: User = Depends(get_current_user)):
    """List notifications."""
    # TODO: query notifications from DB
    return {
        "notifications": [],
        "total": 0,
        "unread_count": 0,
    }


@router.patch("/{notification_id}")
async def acknowledge_notification(
    notification_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Dismiss or acknowledge a notification."""
    # TODO: update notification status
    return {
        "id": str(notification_id),
        "acknowledged": True,
    }


@router.get("/preferences")
async def get_notification_preferences(user: User = Depends(get_current_user)):
    """Get notification preferences."""
    # TODO: fetch user notification preferences
    return {
        "push_enabled": True,
        "email_enabled": False,
        "quiet_hours": {"start": "22:00", "end": "07:00"},
        "categories": {},
    }


@router.patch("/preferences")
async def update_notification_preferences(user: User = Depends(get_current_user)):
    """Update notification preferences."""
    # TODO: accept and apply notification preference updates
    return {
        "push_enabled": True,
        "email_enabled": False,
        "quiet_hours": {"start": "22:00", "end": "07:00"},
        "categories": {},
        "updated": True,
    }
