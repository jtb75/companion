"""Admin API — Escalation monitoring."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import AdminUser, require_admin_role

router = APIRouter(prefix="/admin/escalations", tags=["Admin - Escalations"])

_viewer = require_admin_role("viewer")


@router.get("")
async def list_escalations(admin: AdminUser = Depends(_viewer)):
    """Active escalations."""
    # TODO: query active escalations
    return {
        "escalations": [],
        "total": 0,
    }


@router.get("/history")
async def escalation_history(admin: AdminUser = Depends(_viewer)):
    """Escalation history."""
    # TODO: query escalation history
    return {
        "escalations": [],
        "total": 0,
    }


@router.get("/stats")
async def escalation_stats(admin: AdminUser = Depends(_viewer)):
    """Escalation statistics."""
    # TODO: compute escalation stats
    return {
        "total_24h": 0,
        "total_7d": 0,
        "by_type": {},
        "avg_resolution_time_minutes": 0,
    }
