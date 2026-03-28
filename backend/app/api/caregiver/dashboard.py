"""Caregiver API — Dashboard (Tier 2+)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CaregiverContext, require_tier
from app.db import get_db
from app.models.enums import AccessTier
from app.services import caregiver_service

router = APIRouter(tags=["Caregiver - Dashboard"])


@router.get("/dashboard")
async def get_dashboard(
    caregiver: CaregiverContext = Depends(require_tier(AccessTier.TIER_2)),
    db: AsyncSession = Depends(get_db),
):
    """Summary dashboard for Tier 2+ caregivers."""
    return await caregiver_service.get_dashboard_summary(db, caregiver.user_id)
