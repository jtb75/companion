"""App API — User profile and memory routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, get_current_user
from app.db import get_db
from app.schemas.user import UserUpdate
from app.services import caregiver_service, memory_service

router = APIRouter(prefix="/me", tags=["Users"])


@router.get("")
async def get_profile(user: User = Depends(get_current_user)):
    """Return current user profile."""
    return user


@router.patch("")
async def update_profile(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update profile/preferences."""
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(user, key, value)
    await db.flush()
    return user


@router.get("/memory")
async def list_memories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List functional memories."""
    memories = await memory_service.list_memories(db, user.id)
    return {"memories": memories, "total": len(memories)}


@router.delete("/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific memory."""
    deleted = await memory_service.delete_memory(db, user.id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return None


@router.get("/activity")
async def get_activity(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Caregiver activity log visible to the user."""
    activities = await caregiver_service.get_caregiver_activity(db, user.id)
    return {"activities": activities, "total": len(activities)}
