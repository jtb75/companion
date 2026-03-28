"""App API — Document routes."""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import User, get_current_user

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def scan_document(user: User = Depends(get_current_user)):
    """Submit a camera scan for processing."""
    # TODO: accept image upload, enqueue pipeline processing
    return {
        "id": str(uuid.uuid4()),
        "status": "received",
        "message": "Document scan submitted for processing",
    }


@router.get("")
async def list_documents(
    document_status: str | None = Query(None, alias="status"),
    classification: str | None = None,
    urgency: str | None = None,
    user: User = Depends(get_current_user),
):
    """List documents with optional filters."""
    # TODO: query documents from DB with filters
    return {
        "documents": [],
        "total": 0,
        "filters": {
            "status": document_status,
            "classification": classification,
            "urgency": urgency,
        },
    }


@router.get("/{document_id}")
async def get_document(document_id: uuid.UUID, user: User = Depends(get_current_user)):
    """Get document detail."""
    # TODO: fetch document from DB
    return {
        "id": str(document_id),
        "status": "summarized",
        "classification": "bill",
        "urgency": "routine",
        "summary": "Placeholder document summary",
        "created_at": "2026-01-15T10:00:00Z",
    }


@router.patch("/{document_id}")
async def update_document(document_id: uuid.UUID, user: User = Depends(get_current_user)):
    """Update document status."""
    # TODO: accept and apply document update payload
    return {
        "id": str(document_id),
        "status": "acknowledged",
        "updated": True,
    }


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, user: User = Depends(get_current_user)):
    """Delete a document."""
    # TODO: soft-delete document
    return None
