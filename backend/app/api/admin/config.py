"""Admin API — Configuration management."""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import AdminUser, require_admin_role

router = APIRouter(prefix="/admin/config", tags=["Admin - Config"])

_viewer = require_admin_role("viewer")
_editor = require_admin_role("editor")


@router.get("")
async def list_config(admin: AdminUser = Depends(_viewer)):
    """List all configuration entries."""
    # TODO: query config entries from DB
    return {
        "entries": [],
        "total": 0,
    }


@router.get("/audit")
async def full_audit_log(admin: AdminUser = Depends(_viewer)):
    """Full configuration audit log."""
    # TODO: query full audit log
    return {
        "entries": [],
        "total": 0,
    }


@router.get("/{config_id}")
async def get_config(config_id: uuid.UUID, admin: AdminUser = Depends(_viewer)):
    """Get a configuration entry with history."""
    # TODO: fetch config entry with version history
    return {
        "id": str(config_id),
        "category": "feature_flag",
        "key": "placeholder_key",
        "value": {},
        "version": 1,
        "history": [],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_config(admin: AdminUser = Depends(_editor)):
    """Create a new configuration entry."""
    # TODO: accept config payload and persist
    return {
        "id": str(uuid.uuid4()),
        "category": "feature_flag",
        "key": "new_key",
        "value": {},
        "version": 1,
        "created": True,
    }


@router.patch("/{config_id}")
async def update_config(config_id: uuid.UUID, admin: AdminUser = Depends(_editor)):
    """Update a configuration entry."""
    # TODO: accept and apply config update, create audit entry
    return {
        "id": str(config_id),
        "version": 2,
        "updated": True,
    }


@router.get("/{config_id}/history")
async def config_history(config_id: uuid.UUID, admin: AdminUser = Depends(_viewer)):
    """Audit log for a specific configuration entry."""
    # TODO: query audit log for this config entry
    return {
        "config_id": str(config_id),
        "history": [],
        "total": 0,
    }
