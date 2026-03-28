"""App API — Bill routes."""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/bills", tags=["Bills"])


@router.get("")
async def list_bills(
    bill_status: str | None = Query(None, alias="status"),
    due_after: str | None = Query(None),
    due_before: str | None = Query(None),
    user: User = Depends(get_current_user),
):
    """List bills with optional filters."""
    # TODO: query bills from DB with filters
    return {
        "bills": [],
        "total": 0,
        "filters": {
            "status": bill_status,
            "due_after": due_after,
            "due_before": due_before,
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_bill(user: User = Depends(get_current_user)):
    """Create a new bill."""
    # TODO: accept bill payload and persist
    return {
        "id": str(uuid.uuid4()),
        "payee": "Placeholder Payee",
        "amount": 0.00,
        "due_date": "2026-04-15",
        "status": "pending",
        "created": True,
    }


@router.patch("/{bill_id}")
async def update_bill(bill_id: uuid.UUID, user: User = Depends(get_current_user)):
    """Update a bill."""
    # TODO: accept and apply bill update payload
    return {
        "id": str(bill_id),
        "updated": True,
    }


@router.get("/summary")
async def bill_summary(user: User = Depends(get_current_user)):
    """Monthly bill summary."""
    # TODO: compute monthly summary from DB
    return {
        "month": "2026-03",
        "total_due": 0.00,
        "total_paid": 0.00,
        "overdue_count": 0,
        "upcoming_count": 0,
    }
