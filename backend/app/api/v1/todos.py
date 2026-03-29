"""App API — Todo routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, require_complete_profile
from app.db import get_db
from app.schemas.todo import TodoCreate, TodoUpdate
from app.services import todo_service

router = APIRouter(prefix="/todos", tags=["Todos"])


@router.get("")
async def list_todos(
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """List all todos."""
    todos = await todo_service.list_todos(db, user.id)
    return {"todos": todos, "total": len(todos)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_todo(
    data: TodoCreate,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Create a new todo."""
    todo = await todo_service.create_todo(db, user.id, data.model_dump())
    return todo


@router.patch("/{todo_id}")
async def update_todo(
    todo_id: uuid.UUID,
    data: TodoUpdate,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Update a todo."""
    todo = await todo_service.update_todo(
        db, user.id, todo_id, data.model_dump(exclude_unset=True)
    )
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Delete a todo."""
    deleted = await todo_service.delete_todo(db, user.id, todo_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Todo not found")
    return None


@router.post("/{todo_id}/complete")
async def complete_todo(
    todo_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Mark a todo as complete."""
    todo = await todo_service.complete_todo(db, user.id, todo_id)
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo
