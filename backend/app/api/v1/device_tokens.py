"""App API — Device token registration for push notifications."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, get_current_user
from app.db import get_db
from app.services import device_token_service

router = APIRouter(prefix="/me/devices", tags=["Device Tokens"])


class DeviceTokenRegister(BaseModel):
    fcm_token: str
    platform: str
    device_name: str | None = None


class DeviceTokenDeactivate(BaseModel):
    fcm_token: str


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_device_token(
    data: DeviceTokenRegister,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register an FCM device token for push notifications."""
    token = await device_token_service.register_token(
        db,
        user.id,
        data.fcm_token,
        data.platform,
        data.device_name,
    )
    await db.commit()
    return {
        "id": str(token.id),
        "fcm_token": token.fcm_token,
        "platform": token.device_platform,
        "is_active": token.is_active,
    }


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_device_token(
    data: DeviceTokenDeactivate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an FCM device token."""
    found = await device_token_service.deactivate_token(
        db, user.id, data.fcm_token
    )
    if not found:
        raise HTTPException(
            status_code=404, detail="Token not found"
        )
    await db.commit()
    return None
