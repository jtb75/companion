"""Caregiver API — Safety alerts (Tier 1+)."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import CaregiverContext, require_tier
from app.models.enums import AccessTier

router = APIRouter(tags=["Caregiver - Alerts"])


@router.get("/alerts")
async def get_alerts(
    caregiver: CaregiverContext = Depends(require_tier(AccessTier.TIER_1)),
):
    """Active safety alerts visible to Tier 1+ caregivers."""
    # TODO: query active safety alerts for the caregiver's linked user
    return {
        "alerts": [],
        "total": 0,
    }
