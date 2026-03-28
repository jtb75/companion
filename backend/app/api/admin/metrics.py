"""Admin API — Business metrics."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import AdminUser, require_admin_role

router = APIRouter(prefix="/admin/metrics", tags=["Admin - Metrics"])

_viewer = require_admin_role("viewer")


@router.get("/engagement")
async def engagement_metrics(admin: AdminUser = Depends(_viewer)):
    """User engagement metrics."""
    # TODO: compute engagement metrics
    return {
        "daily_active_users": 0,
        "weekly_active_users": 0,
        "avg_session_duration_minutes": 0,
        "conversations_per_user_avg": 0,
    }


@router.get("/onboarding")
async def onboarding_metrics(admin: AdminUser = Depends(_viewer)):
    """Onboarding funnel metrics."""
    # TODO: compute onboarding metrics
    return {
        "started": 0,
        "completed": 0,
        "completion_rate": 0.0,
        "avg_duration_minutes": 0,
        "drop_off_step": None,
    }


@router.get("/retention")
async def retention_metrics(admin: AdminUser = Depends(_viewer)):
    """User retention metrics."""
    # TODO: compute retention metrics
    return {
        "day_1": 0.0,
        "day_7": 0.0,
        "day_30": 0.0,
        "cohorts": [],
    }


@router.get("/checkin")
async def checkin_metrics(admin: AdminUser = Depends(_viewer)):
    """Daily check-in metrics."""
    # TODO: compute check-in metrics
    return {
        "checkins_today": 0,
        "checkins_7d": 0,
        "avg_checkins_per_user": 0.0,
    }


@router.get("/documents")
async def document_metrics(admin: AdminUser = Depends(_viewer)):
    """Document processing metrics."""
    # TODO: compute document metrics
    return {
        "total_processed": 0,
        "by_classification": {},
        "by_source": {},
        "avg_processing_time_ms": 0,
    }
