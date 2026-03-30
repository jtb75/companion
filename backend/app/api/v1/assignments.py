"""App API — Assignment routes (caregiver-to-member assignment requests)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, require_complete_profile
from app.db import get_db
from app.integrations.email_service import (
    send_assignment_approved_notification,
    send_assignment_rejected_notification,
)
from app.models.assignment_request import CaregiverAssignmentRequest
from app.schemas.invitation import (
    AssignmentApproveResponse,
    AssignmentRejectResponse,
    AssignmentRequestResponse,
)
from app.services import assignment_service

router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.get("/pending", response_model=list[AssignmentRequestResponse])
async def list_pending_assignments(
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """List pending caregiver assignment requests for this member."""
    requests = await assignment_service.list_pending_assignments(db, user.id)
    return requests


@router.post("/{request_id}/approve", response_model=AssignmentApproveResponse)
async def approve_assignment(
    request_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Member approves a caregiver assignment request."""
    try:
        contact = await assignment_service.approve_assignment(db, request_id, user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Notify the caregiver
    if contact.contact_email:
        await send_assignment_approved_notification(
            to_email=contact.contact_email,
            to_name=contact.contact_name,
            member_name=user.preferred_name or user.display_name,
        )

    return AssignmentApproveResponse(approved=True, contact_id=contact.id)


@router.post("/{request_id}/reject", response_model=AssignmentRejectResponse)
async def reject_assignment(
    request_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Member rejects a caregiver assignment request. Returns 403 for managed accounts."""
    try:
        request = await assignment_service.reject_assignment(db, request_id, user.id)
    except PermissionError:
        raise HTTPException(
            403, "Your account is managed by your organization. Contact your administrator."
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Notify the caregiver
    await send_assignment_rejected_notification(
        to_email=request.caregiver_email,
        to_name=request.caregiver_name,
        member_name=user.preferred_name or user.display_name,
    )

    return AssignmentRejectResponse(rejected=True)
