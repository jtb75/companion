"""App API — Bill routes."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, get_current_user
from app.db import get_db
from app.schemas.bill import BillCreate, BillUpdate
from app.services import bill_service

router = APIRouter(prefix="/bills", tags=["Bills"])


@router.get("")
async def list_bills(
    bill_status: str | None = Query(None, alias="status"),
    due_after: date | None = Query(None),
    due_before: date | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List bills with optional filters."""
    bills = await bill_service.list_bills(
        db, user.id, status=bill_status, due_after=due_after, due_before=due_before
    )
    return {"bills": bills, "total": len(bills)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_bill(
    data: BillCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new bill."""
    bill = await bill_service.create_bill(db, user.id, data.model_dump())
    return bill


@router.patch("/{bill_id}")
async def update_bill(
    bill_id: uuid.UUID,
    data: BillUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a bill."""
    bill = await bill_service.update_bill(
        db, user.id, bill_id, data.model_dump(exclude_unset=True)
    )
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill


@router.get("/summary")
async def bill_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Monthly bill summary."""
    summary = await bill_service.get_bill_summary(db, user.id)
    return summary
