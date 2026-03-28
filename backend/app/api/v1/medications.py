"""App API — Medication routes."""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/medications", tags=["Medications"])


@router.get("")
async def list_medications(user: User = Depends(get_current_user)):
    """List all medications."""
    # TODO: query medications from DB
    return {
        "medications": [],
        "total": 0,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_medication(user: User = Depends(get_current_user)):
    """Add a new medication."""
    # TODO: accept medication payload and persist
    return {
        "id": str(uuid.uuid4()),
        "name": "Placeholder Medication",
        "dosage": "500mg",
        "frequency": "twice daily",
        "created": True,
    }


@router.patch("/{medication_id}")
async def update_medication(
    medication_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Update a medication."""
    # TODO: accept and apply medication update payload
    return {
        "id": str(medication_id),
        "updated": True,
    }


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Remove a medication."""
    # TODO: soft-delete medication
    return None


@router.post("/{medication_id}/confirm", status_code=status.HTTP_201_CREATED)
async def confirm_dose(
    medication_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Confirm a dose was taken."""
    # TODO: record dose confirmation
    return {
        "medication_id": str(medication_id),
        "confirmed_at": "2026-03-27T12:00:00Z",
        "confirmed": True,
    }


@router.get("/{medication_id}/history")
async def dose_history(
    medication_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Get dose confirmation history."""
    # TODO: query dose confirmation history
    return {
        "medication_id": str(medication_id),
        "confirmations": [],
        "total": 0,
    }
