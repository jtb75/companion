"""Caregiver API — Safety alerts (Tier 1+)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CaregiverContext, require_tier
from app.db import get_db
from app.models.enums import AccessTier
from app.services import caregiver_service

router = APIRouter(tags=["Caregiver - Alerts"])


@router.get("/alerts")
async def get_alerts(
    caregiver: CaregiverContext = Depends(require_tier(AccessTier.TIER_1)),
    db: AsyncSession = Depends(get_db),
):
    """Active safety alerts visible to Tier 1+ caregivers."""
    alerts = await caregiver_service.get_alerts(db, caregiver.user_id)
    return {"alerts": alerts, "total": len(alerts)}
