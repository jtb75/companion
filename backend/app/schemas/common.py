from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Meta(BaseModel):
    request_id: str
    timestamp: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    has_more: bool


class PaginatedResponse(BaseModel):
    """Generic paginated response. Subclass with specific data type."""

    meta: PaginationMeta


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
