"""App API — Appointment routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, get_current_user
from app.db import get_db
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services import appointment_service

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("")
async def list_appointments(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all appointments."""
    appointments = await appointment_service.list_appointments(db, user.id)
    return {"appointments": appointments, "total": len(appointments)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    data: AppointmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new appointment."""
    appointment = await appointment_service.create_appointment(
        db, user.id, data.model_dump()
    )
    return appointment


@router.patch("/{appointment_id}")
async def update_appointment(
    appointment_id: uuid.UUID,
    data: AppointmentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an appointment."""
    appointment = await appointment_service.update_appointment(
        db, user.id, appointment_id, data.model_dump(exclude_unset=True)
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an appointment."""
    deleted = await appointment_service.delete_appointment(db, user.id, appointment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return None


@router.post("/{appointment_id}/travel", status_code=status.HTTP_201_CREATED)
async def request_travel_plan(
    appointment_id: uuid.UUID,
    user: User = Depends(get_current_user),
):
    """Request a travel plan for an appointment.

    Stub — involves external services not in Phase 3.
    """
    return {
        "appointment_id": str(appointment_id),
        "travel_plan": None,
        "status": "pending",
    }
