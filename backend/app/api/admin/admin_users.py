"""Admin API — Admin user management."""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import AdminUser, require_admin_role

router = APIRouter(prefix="/admin/users", tags=["Admin - Users"])

_admin = require_admin_role("admin")


@router.get("")
async def list_admin_users(admin: AdminUser = Depends(_admin)):
    """List all admin users."""
    # TODO: query admin users from DB
    return {
        "users": [],
        "total": 0,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_admin_user(admin: AdminUser = Depends(_admin)):
    """Create a new admin user."""
    # TODO: accept admin user payload and persist
    return {
        "id": str(uuid.uuid4()),
        "email": "new-admin@example.com",
        "role": "viewer",
        "is_active": True,
        "created": True,
    }


@router.patch("/{user_id}")
async def update_admin_user(
    user_id: uuid.UUID, admin: AdminUser = Depends(_admin)
):
    """Update an admin user."""
    # TODO: accept and apply admin user update payload
    return {
        "id": str(user_id),
        "updated": True,
    }


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user(
    user_id: uuid.UUID, admin: AdminUser = Depends(_admin)
):
    """Delete an admin user."""
    # TODO: deactivate admin user
    return None
