"""Admin API — Unified People management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AdminUser, require_admin_role
from app.db import get_db
from app.integrations.email_service import (
    send_assignment_request_notification,
    send_caregiver_invitation,
    send_platform_invitation,
)
from app.models.admin_user import AdminUser as AdminUserModel
from app.models.enums import CareModel
from app.models.trusted_contact import TrustedContact
from app.models.user import User
from app.schemas.invitation import AdminPlatformInvite, AdminPlatformInviteResponse
from app.services import assignment_service, invitation_service

_editor = require_admin_role("editor")

router = APIRouter(tags=["Admin - People"])


@router.get("/admin/people")
async def list_all_people(
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """List all people in the system with their consolidated roles."""

    # Get all companion users
    users_result = await db.execute(select(User).order_by(User.first_name))
    users = users_result.scalars().all()

    # Get all admin users
    admins_result = await db.execute(select(AdminUserModel))
    admins = admins_result.scalars().all()
    admin_by_email = {a.email: a for a in admins}

    # Get all trusted contacts
    contacts_result = await db.execute(
        select(TrustedContact, User)
        .join(User, TrustedContact.user_id == User.id)
    )
    contact_rows = contacts_result.all()

    # Build a map of caregiver assignments by contact_email
    # Each email may be a caregiver for multiple users
    caregiver_map: dict[str, list[dict]] = {}
    for contact, user in contact_rows:
        email = contact.contact_email
        if email:
            if email not in caregiver_map:
                caregiver_map[email] = []
            caregiver_map[email].append({
                "contact_id": str(contact.id),
                "user_id": str(contact.user_id),
                "user_name": user.display_name or user.preferred_name,
                "contact_name": contact.contact_name,
                "relationship": getattr(
                    contact.relationship_type, "value",
                    str(contact.relationship_type),
                ),
                "tier": getattr(
                    contact.access_tier, "value",
                    str(contact.access_tier),
                ),
                "is_active": contact.is_active,
                "invitation_status": contact.invitation_status,
            })

    # Build consolidated people list
    # Start with all users, then add admin-only people not in users table
    people = []
    seen_emails: set[str] = set()

    for u in users:
        email = u.email
        seen_emails.add(email)
        admin_record = admin_by_email.get(email)

        people.append({
            "id": str(u.id),
            "email": email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "phone": u.phone,
            "preferred_name": u.preferred_name,
            "display_name": u.display_name,
            "is_user": True,
            "is_admin": admin_record is not None,
            "admin_id": str(admin_record.id) if admin_record else None,
            "admin_role": admin_record.role if admin_record else None,
            "care_model": u.care_model,
            "account_status": u.account_status,
            "caregiver_for": caregiver_map.get(email, []),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    # Add admin-only people (not in users table)
    for a in admins:
        if a.email not in seen_emails:
            seen_emails.add(a.email)
            people.append({
                "id": None,
                "email": a.email,
                "first_name": a.name,
                "last_name": None,
                "phone": None,
                "preferred_name": a.name,
                "display_name": a.name,
                "is_user": False,
                "is_admin": True,
                "admin_id": str(a.id),
                "admin_role": a.role,
                "care_model": None,
                "account_status": None,
                "caregiver_for": caregiver_map.get(a.email, []),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    # Add caregiver-only people (in trusted_contacts but not in users or admins)
    for email, assignments in caregiver_map.items():
        if email and email not in seen_emails:
            seen_emails.add(email)
            people.append({
                "id": None,
                "email": email,
                "first_name": assignments[0]["contact_name"] if assignments else None,
                "last_name": None,
                "phone": None,
                "preferred_name": assignments[0]["contact_name"] if assignments else email,
                "display_name": assignments[0]["contact_name"] if assignments else email,
                "is_user": False,
                "is_admin": False,
                "admin_id": None,
                "admin_role": None,
                "care_model": None,
                "account_status": None,
                "caregiver_for": assignments,
                "created_at": None,
            })

    return {"people": people, "total": len(people)}


@router.post("/admin/people", status_code=status.HTTP_201_CREATED)
async def create_person(
    data: dict,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Create a new person — optionally as user, admin, and/or caregiver."""
    email = data.get("email")
    if not email:
        raise HTTPException(400, "Email required")

    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    phone = data.get("phone")

    user_id = None

    # Create user record if requested
    if data.get("is_user", True):
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(409, "User with this email already exists")

        care_model = data.get("care_model", CareModel.SELF_DIRECTED)
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            preferred_name=data.get("preferred_name", first_name),
            display_name=f"{first_name} {last_name}".strip() or email,
            primary_language="en",
            voice_id="warm",
            pace_setting="normal",
            warmth_level="warm",
            care_model=care_model,
        )
        db.add(user)
        await db.flush()
        user_id = str(user.id)

    # Create admin record if requested
    admin_id = None
    if data.get("is_admin"):
        admin_record = AdminUserModel(
            email=email,
            name=f"{first_name} {last_name}".strip() or email,
            role=data.get("admin_role", "viewer"),
            is_active=True,
        )
        db.add(admin_record)
        await db.flush()
        admin_id = str(admin_record.id)

    return {
        "created": True,
        "user_id": user_id,
        "admin_id": admin_id,
    }


@router.patch("/admin/people/{email}")
async def update_person(
    email: str,
    data: dict,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Update a person's details and roles."""

    # Update user record if exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        for field in ["first_name", "last_name", "phone", "preferred_name", "care_model"]:
            if field in data:
                setattr(user, field, data[field])
        if "first_name" in data or "last_name" in data:
            first = data.get("first_name", user.first_name) or ""
            last = data.get("last_name", user.last_name) or ""
            user.display_name = f"{first} {last}".strip() or email

    # Handle admin role changes
    result = await db.execute(
        select(AdminUserModel).where(AdminUserModel.email == email)
    )
    admin_record = result.scalar_one_or_none()

    if data.get("is_admin") and not admin_record:
        # Add as admin
        admin_record = AdminUserModel(
            email=email,
            name=user.display_name if user else email,
            role=data.get("admin_role", "viewer"),
            is_active=True,
        )
        db.add(admin_record)
    elif not data.get("is_admin") and admin_record and "is_admin" in data:
        # Remove admin
        await db.delete(admin_record)
    elif admin_record and "admin_role" in data:
        # Update admin role
        admin_record.role = data["admin_role"]

    await db.flush()
    return {"updated": True}


@router.post("/admin/people/{email}/invite", status_code=status.HTTP_201_CREATED)
async def invite_to_platform(
    email: str,
    data: AdminPlatformInvite,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Invite someone to the platform (Part 1 — no member assignment)."""
    user, created = await invitation_service.create_admin_platform_invitation(
        db=db, admin_id=admin.id, email=email, name=data.name,
    )

    email_sent = await send_platform_invitation(
        to_email=email,
        to_name=data.name,
        invited_by=admin.name,
    )

    return AdminPlatformInviteResponse(
        user_id=user.id,
        account_status=user.account_status,
        email_sent=email_sent,
        already_existed=not created,
    )


@router.post("/admin/people/{email}/caregiver")
async def add_caregiver_assignment(
    email: str,
    data: dict,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Assign this person as a caregiver for a member.

    For managed members: creates TrustedContact immediately.
    For self-directed members: creates an assignment request pending member approval.
    """
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(400, "user_id required")

    member = await db.get(User, uuid.UUID(user_id))
    if not member:
        raise HTTPException(404, "Member not found")

    contact_name = data.get("contact_name", email)
    relationship = data.get("relationship", "family")
    tier = data.get("tier", "tier_1")

    # Ensure caregiver has a stub account
    await invitation_service.get_or_create_stub_user(db, email, contact_name)

    try:
        result = await assignment_service.create_assignment_request(
            db=db,
            member_id=member.id,
            caregiver_email=email,
            caregiver_name=contact_name,
            relationship_type=relationship,
            access_tier=tier,
            initiated_by="admin",
            admin_id=admin.id,
        )
    except ValueError as e:
        raise HTTPException(409, str(e)) from None

    member_name = member.preferred_name or member.display_name

    if isinstance(result, TrustedContact):
        # Managed — direct assignment, send invitation email
        await send_caregiver_invitation(
            to_email=email,
            to_name=contact_name,
            user_name=member_name,
            relationship=relationship,
            invited_by=admin.name,
        )
        return {"created": True, "contact_id": str(result.id), "status": "assigned"}
    else:
        # Self-directed — pending approval, notify both parties
        await send_caregiver_invitation(
            to_email=email,
            to_name=contact_name,
            user_name=member_name,
            relationship=relationship,
            invited_by=admin.name,
        )
        await send_assignment_request_notification(
            to_email=member.email,
            to_name=member_name,
            caregiver_name=contact_name,
            relationship=relationship,
        )
        return {"created": True, "request_id": str(result.id), "status": "pending_approval"}


@router.delete("/admin/people/caregiver/{contact_id}")
async def remove_caregiver_assignment(
    contact_id: uuid.UUID,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Remove a caregiver assignment."""
    contact = await db.get(TrustedContact, contact_id)
    if not contact:
        raise HTTPException(404, "Contact not found")
    await db.delete(contact)
    await db.flush()
    return {"deleted": True}
