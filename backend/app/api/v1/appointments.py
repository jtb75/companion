"""App API — Appointment routes."""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("")
async def list_appointments(user: User = Depends(get_current_user)):
    """List all appointments."""
    # TODO: query appointments from DB
    return {
        "appointments": [],
        "total": 0,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_appointment(user: User = Depends(get_current_user)):
    """Create a new appointment."""
    # TODO: accept appointment payload and persist
    return {
        "id": str(uuid.uuid4()),
        "title": "Placeholder Appointment",
        "date": "2026-04-01T10:00:00Z",
        "created": True,
    }


@router.patch("/{appointment_id}")
async def update_appointment(
    appointment_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Update an appointment."""
    # TODO: accept and apply appointment update payload
    return {
        "id": str(appointment_id),
        "updated": True,
    }


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Delete an appointment."""
    # TODO: soft-delete appointment
    return None


@router.post("/{appointment_id}/travel", status_code=status.HTTP_201_CREATED)
async def request_travel_plan(
    appointment_id: uuid.UUID, user: User = Depends(get_current_user)
):
    """Request a travel plan for an appointment."""
    # TODO: generate travel plan via external service
    return {
        "appointment_id": str(appointment_id),
        "travel_plan": {
            "departure_time": "2026-04-01T09:00:00Z",
            "mode": "bus",
            "estimated_duration_minutes": 45,
            "steps": [],
        },
        "created": True,
    }
