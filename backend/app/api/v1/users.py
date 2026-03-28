"""App API — User profile and memory routes."""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/me", tags=["Users"])


@router.get("")
async def get_profile(user: User = Depends(get_current_user)):
    """Return current user profile."""
    # TODO: return real user profile from DB
    return {
        "id": str(user.id),
        "display_name": "Dev User",
        "email": "dev@example.com",
        "preferences": {},
        "created_at": "2026-01-01T00:00:00Z",
    }


@router.patch("")
async def update_profile(user: User = Depends(get_current_user)):
    """Update profile/preferences."""
    # TODO: accept and apply profile update payload
    return {
        "id": str(user.id),
        "display_name": "Dev User",
        "email": "dev@example.com",
        "preferences": {},
        "updated": True,
    }


@router.get("/memory")
async def list_memories(user: User = Depends(get_current_user)):
    """List functional memories."""
    # TODO: query memory store
    return {
        "memories": [
            {
                "id": str(uuid.uuid4()),
                "category": "medication",
                "content": "Takes metformin 500mg twice daily",
                "source": "user_input",
                "created_at": "2026-01-15T10:00:00Z",
            }
        ],
        "total": 1,
    }


@router.delete("/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: uuid.UUID, user: User = Depends(get_current_user)):
    """Delete a specific memory."""
    # TODO: delete memory from store
    return None


@router.get("/activity")
async def get_activity(user: User = Depends(get_current_user)):
    """Caregiver activity log visible to the user."""
    # TODO: query caregiver activity log
    return {
        "activities": [],
        "total": 0,
    }
