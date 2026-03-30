"""Service layer for caregiver-to-member assignment (Part 2)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment_request import CaregiverAssignmentRequest
from app.models.enums import (
    AssignmentRequestStatus,
    CareModel,
    InvitationStatus,
)
from app.models.trusted_contact import TrustedContact
from app.models.user import User

ASSIGNMENT_TTL_DAYS = 14


async def create_assignment_request(
    db: AsyncSession,
    member_id: UUID,
    caregiver_email: str,
    caregiver_name: str,
    relationship_type: str,
    access_tier: str = "tier_1",
    initiated_by: str = "admin",
    admin_id: UUID | None = None,
) -> CaregiverAssignmentRequest | TrustedContact:
    """Create an assignment request or auto-approve for managed members.

    Returns CaregiverAssignmentRequest if pending, or TrustedContact if auto-approved.
    """
    # Check member's care model
    result = await db.execute(select(User).where(User.id == member_id))
    member = result.scalar_one_or_none()
    if member is None:
        raise ValueError("Member not found")

    # Check for existing active assignment
    existing = await db.execute(
        select(TrustedContact).where(
            TrustedContact.user_id == member_id,
            TrustedContact.contact_email == caregiver_email,
            TrustedContact.is_active.is_(True),
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Caregiver is already assigned to this member")

    # Check for existing pending request
    pending = await db.execute(
        select(CaregiverAssignmentRequest).where(
            CaregiverAssignmentRequest.member_id == member_id,
            CaregiverAssignmentRequest.caregiver_email == caregiver_email,
            CaregiverAssignmentRequest.status == AssignmentRequestStatus.PENDING_APPROVAL,
        )
    )
    if pending.scalar_one_or_none():
        raise ValueError("A pending assignment request already exists")

    now = datetime.now(UTC)

    if member.care_model == CareModel.MANAGED:
        # Auto-approve: create TrustedContact directly
        contact = TrustedContact(
            user_id=member_id,
            contact_name=caregiver_name,
            contact_email=caregiver_email,
            relationship_type=relationship_type,
            access_tier=access_tier,
            is_active=True,
            invitation_status=InvitationStatus.ACCEPTED,
            accepted_at=now,
            invited_by_admin_id=admin_id,
        )
        db.add(contact)
        await db.flush()
        return contact

    # Self-directed: create pending request
    request = CaregiverAssignmentRequest(
        member_id=member_id,
        caregiver_email=caregiver_email,
        caregiver_name=caregiver_name,
        relationship_type=relationship_type,
        access_tier=access_tier,
        status=AssignmentRequestStatus.PENDING_APPROVAL,
        initiated_by=initiated_by,
        initiated_by_admin_id=admin_id,
        expires_at=now + timedelta(days=ASSIGNMENT_TTL_DAYS),
    )
    db.add(request)
    await db.flush()
    return request


async def list_pending_assignments(
    db: AsyncSession, member_id: UUID
) -> list[CaregiverAssignmentRequest]:
    """List pending assignment requests for a member."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(CaregiverAssignmentRequest).where(
            CaregiverAssignmentRequest.member_id == member_id,
            CaregiverAssignmentRequest.status == AssignmentRequestStatus.PENDING_APPROVAL,
            CaregiverAssignmentRequest.expires_at > now,
        ).order_by(CaregiverAssignmentRequest.requested_at.desc())
    )
    return list(result.scalars().all())


async def approve_assignment(
    db: AsyncSession, request_id: UUID, member_id: UUID
) -> TrustedContact:
    """Member approves an assignment request. Creates TrustedContact."""
    result = await db.execute(
        select(CaregiverAssignmentRequest).where(
            CaregiverAssignmentRequest.id == request_id,
            CaregiverAssignmentRequest.member_id == member_id,
            CaregiverAssignmentRequest.status == AssignmentRequestStatus.PENDING_APPROVAL,
        )
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise ValueError("Assignment request not found or already resolved")

    now = datetime.now(UTC)

    # Resolve the request
    request.status = AssignmentRequestStatus.APPROVED
    request.resolved_at = now
    request.resolved_by = "member"

    # Create the TrustedContact
    contact = TrustedContact(
        user_id=member_id,
        contact_name=request.caregiver_name,
        contact_email=request.caregiver_email,
        relationship_type=request.relationship_type,
        access_tier=request.access_tier,
        is_active=True,
        invitation_status=InvitationStatus.ACCEPTED,
        accepted_at=now,
    )
    db.add(contact)
    await db.flush()
    return contact


async def reject_assignment(
    db: AsyncSession, request_id: UUID, member_id: UUID
) -> CaregiverAssignmentRequest:
    """Member rejects an assignment request."""
    # Check care model
    user_result = await db.execute(select(User).where(User.id == member_id))
    member = user_result.scalar_one_or_none()
    if member and member.care_model == CareModel.MANAGED:
        raise PermissionError("Managed accounts cannot reject caregiver assignments")

    result = await db.execute(
        select(CaregiverAssignmentRequest).where(
            CaregiverAssignmentRequest.id == request_id,
            CaregiverAssignmentRequest.member_id == member_id,
            CaregiverAssignmentRequest.status == AssignmentRequestStatus.PENDING_APPROVAL,
        )
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise ValueError("Assignment request not found or already resolved")

    request.status = AssignmentRequestStatus.REJECTED
    request.resolved_at = datetime.now(UTC)
    request.resolved_by = "member"
    await db.flush()
    return request
