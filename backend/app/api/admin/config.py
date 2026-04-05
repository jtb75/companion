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
    entry = await config_service.create_config(db, {**data.model_dump(), "updated_by": admin.email})
    return entry


@router.patch("/{config_id}")
async def update_config(
    config_id: uuid.UUID,
    data: ConfigUpdateRequest,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Update a configuration entry."""
    # Fetch existing entry to check category
    existing = await config_service.get_config(db, config_id)
    if existing is None:
        raise HTTPException(
            status_code=404, detail="Config entry not found"
        )

    # Enforce immutable bounds for persona config
    if existing.get("category") == "dd_persona":
        _validate_persona_bounds(data.value)

    entry = await config_service.update_config(
        db,
        config_id,
        data.model_dump(exclude_unset=True),
        admin.email,
    )
    if entry is None:
        raise HTTPException(
            status_code=404, detail="Config entry not found"
        )
    return entry


def _validate_persona_bounds(value: dict) -> None:
    """Enforce immutable bounds on persona configuration.

    These bounds cannot be overridden by admin configuration,
    per D.D. Assistant Guidelines Section 3.1.
    """
    reading_level = value.get("reading_level")
    if reading_level is not None:
        try:
            level = int(reading_level)
        except (ValueError, TypeError):
            level = 99
        if level > 8:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Reading level cannot exceed 8th grade "
                    "(Guidelines Section 3.1)"
                ),
            )

    response_length = value.get("response_length")
    if response_length is not None:
        try:
            length = int(response_length)
        except (ValueError, TypeError):
            length = 99
        if length > 7:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Response length cannot exceed 7 sentences "
                    "(Guidelines Section 3.1)"
                ),
            )

    # Cannot disable safety-critical features
    for forbidden_key in (
        "disable_emotional_awareness",
        "disable_confidence_hedging",
        "disable_agency_reinforcement",
    ):
        if value.get(forbidden_key) is True:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Cannot disable {forbidden_key.replace('_', ' ')} "
                    f"(Guidelines Section 3.1)"
                ),
            )


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
