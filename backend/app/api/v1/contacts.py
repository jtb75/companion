"""App API — Trusted contacts routes."""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/contacts", tags=["Trusted Contacts"])


@router.get("")
async def list_contacts(user: User = Depends(get_current_user)):
    """List trusted contacts."""
    # TODO: query trusted contacts from DB
    return {
        "contacts": [],
        "total": 0,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_contact(user: User = Depends(get_current_user)):
    """Add a trusted contact."""
    # TODO: accept contact payload and persist
    return {
        "id": str(uuid.uuid4()),
        "name": "Placeholder Contact",
        "relationship": "family",
        "tier": "tier_1",
        "is_active": True,
        "created": True,
    }


@router.patch("/{contact_id}")
async def update_contact(
    contact_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Update a trusted contact (change tier, scope, etc.)."""
    # TODO: accept and apply contact update payload
    return {
        "id": str(contact_id),
        "updated": True,
    }


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contact(
    contact_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Remove a trusted contact."""
    # TODO: deactivate/remove contact
    return None


@router.post("/{contact_id}/pause")
async def pause_contact(
    contact_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Pause a trusted contact's access."""
    # TODO: set contact is_active = false
    return {
        "id": str(contact_id),
        "is_active": False,
        "paused": True,
    }


@router.post("/{contact_id}/resume")
async def resume_contact(
    contact_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Resume a trusted contact's access."""
    # TODO: set contact is_active = true
    return {
        "id": str(contact_id),
        "is_active": True,
        "resumed": True,
    }
