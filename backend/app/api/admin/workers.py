"""Admin API — Manual worker triggers."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import AdminUser, require_admin_role

router = APIRouter(prefix="/admin/workers", tags=["Admin - Workers"])

_admin = require_admin_role("admin")


@router.post("/deletion")
async def trigger_deletion_worker(admin: AdminUser = Depends(_admin)):
    """Manually trigger the deletion worker."""
    from app.workers.deletion_worker import run_deletion_worker
    result = await run_deletion_worker()
    return {"triggered": True, **result}


@router.post("/retention")
async def trigger_retention_worker(admin: AdminUser = Depends(_admin)):
    """Manually trigger the retention worker."""
    from app.workers.retention import run_retention_worker
    result = await run_retention_worker()
    return {"triggered": True, **(result or {})}


@router.post("/escalation")
async def trigger_escalation_check(admin: AdminUser = Depends(_admin)):
    """Manually trigger the escalation check."""
    from app.workers.escalation_check import run_escalation_check
    result = await run_escalation_check()
    return {"triggered": True, **result}
