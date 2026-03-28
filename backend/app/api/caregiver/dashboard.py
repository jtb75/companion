"""Caregiver API — Dashboard (Tier 2+)."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import CaregiverContext, require_tier
from app.models.enums import AccessTier

router = APIRouter(tags=["Caregiver - Dashboard"])


@router.get("/dashboard")
async def get_dashboard(
    caregiver: CaregiverContext = Depends(require_tier(AccessTier.TIER_2)),
):
    """Summary dashboard for Tier 2+ caregivers."""
    # TODO: aggregate dashboard data for caregiver's linked user
    return {
        "user_summary": {
            "medications_on_track": True,
            "upcoming_appointments": 0,
            "pending_bills": 0,
            "open_todos": 0,
        },
        "recent_activity": [],
        "alerts": [],
    }
