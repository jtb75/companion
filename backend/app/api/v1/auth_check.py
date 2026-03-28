"""Auth check endpoint — called by web dashboard after Firebase login."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorize import authorize_by_email
from app.auth.firebase import verify_firebase_token
from app.config import settings
from app.db import get_db

router = APIRouter(tags=["Auth"])


@router.get("/api/v1/auth/check")
async def check_auth(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Check authorization for the current Firebase user."""

    # Dev/test bypass
    if settings.environment in ("development", "test"):
        if authorization is None:
            return {
                "authorized": True,
                "role": "admin",
                "admin_role": "admin",
                "email": "dev@companion.app",
            }

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        decoded = await verify_firebase_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from None

    email = decoded.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="No email in token")

    auth_result = await authorize_by_email(db, email)

    if not auth_result.is_authorized:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Contact your administrator to request access.",
        )

    response = {
        "authorized": True,
        "role": auth_result.role,
        "email": auth_result.email,
    }

    if auth_result.is_admin:
        response["admin_role"] = auth_result.admin_role

    if auth_result.is_caregiver:
        response["caregiver_users"] = [
            {
                "user_id": str(c.user_id),
                "contact_name": c.contact_name,
                "access_tier": getattr(
                    c.access_tier, "value", str(c.access_tier)
                ),
            }
            for c in auth_result.caregiver_contacts
        ]

    return response
