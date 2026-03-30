"""Profile completion endpoint."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.firebase import verify_firebase_token
from app.config import settings
from app.db import get_db
from app.models.user import User

router = APIRouter(tags=["Profile"])


@router.post("/api/v1/auth/complete-profile")
async def complete_profile(
    data: dict,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Complete user profile with first name, last name, phone."""
    # Dev bypass
    if settings.dev_auth_bypass and not authorization:
        return {"completed": True}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "No token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        decoded = await verify_firebase_token(token)
    except ValueError as e:
        raise HTTPException(401, str(e)) from None

    email = decoded.get("email")
    if not email:
        raise HTTPException(401, "No email")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    phone = data.get("phone") or None
    display = f"{first_name} {last_name}".strip() or email

    if user:
        # Update existing
        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        if phone:
            user.phone = phone
        if data.get("preferred_name"):
            user.preferred_name = data["preferred_name"]
        user.display_name = display
    else:
        # Create new user record (admin or invited user signing in for first time)
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            preferred_name=data.get("preferred_name", first_name),
            display_name=display,
            primary_language="en",
            voice_id="warm",
            pace_setting="normal",
            warmth_level="warm",
        )
        db.add(user)

    await db.flush()
    return {"completed": True, "user_id": str(user.id)}
