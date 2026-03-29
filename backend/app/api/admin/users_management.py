"""Admin API — Companion Users management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AdminUser, require_admin_role
from app.db import get_db
from app.models.user import User

_editor = require_admin_role("editor")

router = APIRouter(tags=["Admin - Users"])


@router.get("/admin/companion-users")
async def list_companion_users(
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """List all companion users with full details."""
    result = await db.execute(select(User).order_by(User.first_name, User.last_name))
    users = result.scalars().all()
    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "phone": u.phone,
                "preferred_name": u.preferred_name,
                "display_name": u.display_name,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    }


@router.post("/admin/companion-users", status_code=status.HTTP_201_CREATED)
async def create_companion_user(
    data: dict,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Create a new companion user."""
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == data.get("email")))
    if result.scalar_one_or_none():
        raise HTTPException(409, "User with this email already exists")

    first = data.get("first_name", "")
    last = data.get("last_name", "")
    user = User(
        email=data["email"],
        first_name=first,
        last_name=last,
        phone=data.get("phone"),
        preferred_name=data.get("preferred_name", first),
        display_name=f"{first} {last}".strip() or data["email"],
        primary_language="en",
        voice_id="warm",
        pace_setting="normal",
        warmth_level="warm",
    )
    db.add(user)
    await db.flush()
    return {"id": str(user.id), "created": True}


@router.patch("/admin/companion-users/{user_id}")
async def update_companion_user(
    user_id: uuid.UUID,
    data: dict,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Update a companion user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    for field in ["first_name", "last_name", "phone", "preferred_name", "email"]:
        if field in data:
            setattr(user, field, data[field])

    # Update display_name if name fields changed
    if "first_name" in data or "last_name" in data:
        first = data.get("first_name", user.first_name) or ""
        last = data.get("last_name", user.last_name) or ""
        user.display_name = f"{first} {last}".strip() or user.email

    await db.flush()
    return {"updated": True}


@router.delete("/admin/companion-users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_companion_user(
    user_id: uuid.UUID,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Delete a companion user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await db.delete(user)
    await db.flush()
    return None
