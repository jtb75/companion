"""Admin API — Configuration management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AdminUser, require_admin_role
from app.db import get_db
from app.schemas.admin import ConfigCreateRequest, ConfigUpdateRequest
from app.services import config_service

router = APIRouter(prefix="/admin/config", tags=["Admin - Config"])

_viewer = require_admin_role("viewer")
_editor = require_admin_role("editor")


@router.get("")
async def list_config(
    admin: AdminUser = Depends(_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List all configuration entries."""
    entries = await config_service.list_config(db)
    return {"entries": entries, "total": len(entries)}


@router.get("/audit")
async def full_audit_log(
    admin: AdminUser = Depends(_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Full configuration audit log."""
    entries = await config_service.get_full_audit_log(db)
    return {"entries": entries, "total": len(entries)}


@router.get("/{config_id}")
async def get_config(
    config_id: uuid.UUID,
    admin: AdminUser = Depends(_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get a configuration entry with history."""
    entry = await config_service.get_config(db, config_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Config entry not found")
    history = await config_service.get_config_history(db, config_id)
    return {
        "entry": entry,
        "history": history,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_config(
    data: ConfigCreateRequest,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Create a new configuration entry."""
    entry = await config_service.create_config(db, admin.email, data.model_dump())
    return entry


@router.patch("/{config_id}")
async def update_config(
    config_id: uuid.UUID,
    data: ConfigUpdateRequest,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Update a configuration entry."""
    entry = await config_service.update_config(
        db, config_id, admin.email, data.model_dump(exclude_unset=True)
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Config entry not found")
    return entry


@router.get("/{config_id}/history")
async def config_history(
    config_id: uuid.UUID,
    admin: AdminUser = Depends(_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Audit log for a specific configuration entry."""
    history = await config_service.get_config_history(db, config_id)
    return {
        "config_id": str(config_id),
        "history": history,
        "total": len(history),
    }
