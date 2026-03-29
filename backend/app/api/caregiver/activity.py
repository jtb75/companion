"""Caregiver API — Activity Log."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.firebase import verify_firebase_token
from app.config import settings
from app.db import get_db
from app.models.trusted_contact import TrustedContact
from app.services import caregiver_service

router = APIRouter(tags=["Caregiver"])


@router.get("/activity")
async def get_activity(
    user_id: uuid.UUID = Query(..., description="User ID to view activity for"),
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Get activity log for a specific user (charge).

    Requires the caller to be assigned as a trusted contact for this user.
    """
    # Dev bypass
    if settings.environment in ("development", "test") and not authorization:
        activity = await caregiver_service.get_caregiver_activity(db, user_id)
        return {"activity": activity}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        decoded = await verify_firebase_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from None

    email = decoded.get("email")

    # Verify this email is assigned as a trusted contact for this user
    result = await db.execute(
        select(TrustedContact).where(
            TrustedContact.contact_email == email,
            TrustedContact.user_id == user_id,
            TrustedContact.is_active.is_(True),
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned as a caregiver for this user",
        )

    activity = await caregiver_service.get_caregiver_activity(db, user_id)
    return {"activity": activity}
