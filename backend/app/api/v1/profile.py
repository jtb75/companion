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

    # Find existing user record — never create new ones
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "No account found. Contact your administrator.")

    # Update existing
    user.first_name = data.get("first_name", user.first_name)
    user.last_name = data.get("last_name", user.last_name)
    user.phone = data.get("phone", user.phone)
    if data.get("preferred_name"):
        user.preferred_name = data["preferred_name"]
    first = user.first_name or ""
    last = user.last_name or ""
    user.display_name = f"{first} {last}".strip() or email

    await db.flush()
    return {"completed": True, "user_id": str(user.id)}
