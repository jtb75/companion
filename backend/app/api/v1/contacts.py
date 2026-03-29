"""App API — Trusted contacts routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, require_complete_profile
from app.db import get_db
from app.schemas.contact import ContactCreate, ContactUpdate
from app.services import caregiver_service

router = APIRouter(prefix="/contacts", tags=["Trusted Contacts"])


@router.get("")
async def list_contacts(
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """List trusted contacts."""
    contacts = await caregiver_service.list_contacts(db, user.id)
    return {"contacts": contacts, "total": len(contacts)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_contact(
    data: ContactCreate,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Add a trusted contact."""
    contact = await caregiver_service.create_contact(db, user.id, data.model_dump())
    return contact


@router.patch("/{contact_id}")
async def update_contact(
    contact_id: uuid.UUID,
    data: ContactUpdate,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Update a trusted contact (change tier, scope, etc.)."""
    contact = await caregiver_service.update_contact(
        db, user.id, contact_id, data.model_dump(exclude_unset=True)
    )
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contact(
    contact_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Remove a trusted contact."""
    deleted = await caregiver_service.delete_contact(db, user.id, contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")
    return None


@router.post("/{contact_id}/pause")
async def pause_contact(
    contact_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Pause a trusted contact's access."""
    contact = await caregiver_service.pause_contact(db, user.id, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/{contact_id}/resume")
async def resume_contact(
    contact_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Resume a trusted contact's access."""
    contact = await caregiver_service.resume_contact(db, user.id, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact
