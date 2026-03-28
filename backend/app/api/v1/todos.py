"""App API — Todo routes."""

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/todos", tags=["Todos"])


@router.get("")
async def list_todos(user: User = Depends(get_current_user)):
    """List all todos."""
    # TODO: query todos from DB
    return {
        "todos": [],
        "total": 0,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_todo(user: User = Depends(get_current_user)):
    """Create a new todo."""
    # TODO: accept todo payload and persist
    return {
        "id": str(uuid.uuid4()),
        "title": "Placeholder Todo",
        "category": "general",
        "source": "user",
        "completed": False,
        "created": True,
    }


@router.patch("/{todo_id}")
async def update_todo(todo_id: uuid.UUID, user: User = Depends(get_current_user)):
    """Update a todo."""
    # TODO: accept and apply todo update payload
    return {
        "id": str(todo_id),
        "updated": True,
    }


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: uuid.UUID, user: User = Depends(get_current_user)):
    """Delete a todo."""
    # TODO: soft-delete todo
    return None


@router.post("/{todo_id}/complete")
async def complete_todo(todo_id: uuid.UUID, user: User = Depends(get_current_user)):
    """Mark a todo as complete."""
    # TODO: mark todo as completed in DB
    return {
        "id": str(todo_id),
        "completed": True,
        "completed_at": "2026-03-27T12:00:00Z",
    }
