from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TodoCategory


class TodoCreate(BaseModel):
    title: str = Field(description="Short task title")
    description: str | None = Field(default=None, description="Detailed description of the task")
    category: TodoCategory = Field(default=TodoCategory.GENERAL, description="Task category")
    due_date: date | None = Field(default=None, description="Optional due date")


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, description="Short task title")
    description: str | None = Field(default=None, description="Detailed description")
    category: TodoCategory | None = Field(default=None, description="Task category")
    due_date: date | None = Field(default=None, description="Due date")
    is_active: bool | None = Field(default=None, description="Whether the task is still active")


class TodoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    category: TodoCategory
    source: str
    due_date: date | None = None
    completed_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
