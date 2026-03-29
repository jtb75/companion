"""App API — Medication routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, require_complete_profile
from app.db import get_db
from app.schemas.medication import MedicationCreate, MedicationUpdate
from app.services import medication_service

router = APIRouter(prefix="/medications", tags=["Medications"])


@router.get("")
async def list_medications(
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """List all medications."""
    meds = await medication_service.list_medications(db, user.id)
    return {"medications": meds, "total": len(meds)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_medication(
    data: MedicationCreate,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Add a new medication."""
    med = await medication_service.create_medication(db, user.id, data.model_dump())
    return med


@router.patch("/{medication_id}")
async def update_medication(
    medication_id: uuid.UUID,
    data: MedicationUpdate,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Update a medication."""
    med = await medication_service.update_medication(
        db, user.id, medication_id, data.model_dump(exclude_unset=True)
    )
    if med is None:
        raise HTTPException(status_code=404, detail="Medication not found")
    return med


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Remove a medication."""
    deleted = await medication_service.delete_medication(db, user.id, medication_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Medication not found")
    return None


@router.post("/{medication_id}/confirm", status_code=status.HTTP_201_CREATED)
async def confirm_dose(
    medication_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Confirm a dose was taken."""
    try:
        confirmation = await medication_service.confirm_dose(db, user.id, medication_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    return confirmation


@router.get("/{medication_id}/history")
async def dose_history(
    medication_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Get dose confirmation history."""
    med = await medication_service.get_medication(db, user.id, medication_id)
    if med is None:
        raise HTTPException(status_code=404, detail="Medication not found")
    confirmations = await medication_service.get_dose_history(db, medication_id)
    return {
        "medication_id": str(medication_id),
        "confirmations": confirmations,
        "total": len(confirmations),
    }
