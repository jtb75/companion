"""Caregiver API — Collaboration (Tier 3)."""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import CaregiverContext, require_tier
from app.models.enums import AccessTier

router = APIRouter(tags=["Caregiver - Collaboration"])


@router.get("/collaboration/{scope_id}")
async def view_scoped_item(
    scope_id: uuid.UUID,
    caregiver: CaregiverContext = Depends(require_tier(AccessTier.TIER_3)),
):
    """View a scoped item (Tier 3 only)."""
    # TODO: fetch the scoped item and verify caregiver has scope access
    return {
        "scope_id": str(scope_id),
        "type": "placeholder",
        "data": {},
    }


@router.post(
    "/collaboration/{scope_id}/comment", status_code=status.HTTP_201_CREATED
)
async def add_comment(
    scope_id: uuid.UUID,
    caregiver: CaregiverContext = Depends(require_tier(AccessTier.TIER_3)),
):
    """Add a comment to a scoped item (Tier 3 only)."""
    # TODO: accept comment payload, persist, notify user
    return {
        "comment_id": str(uuid.uuid4()),
        "scope_id": str(scope_id),
        "body": "Placeholder comment",
        "created_at": "2026-03-27T12:00:00Z",
    }
