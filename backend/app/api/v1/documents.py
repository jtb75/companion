"""App API — Document routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, require_complete_profile
from app.db import get_db
from app.pipeline.orchestrator import process_document
from app.schemas.document import DocumentScanRequest, DocumentStatusUpdate
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def scan_document(
    data: DocumentScanRequest,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Submit a camera scan for processing."""
    doc = await document_service.create_document(db, user.id, data.model_dump())

    # Run the document through the 6-stage intelligence pipeline (V1: synchronous)
    await process_document(db, doc.id, user.id)

    return doc


@router.get("")
async def list_documents(
    document_status: str | None = Query(None, alias="status"),
    classification: str | None = None,
    urgency: str | None = None,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """List documents with optional filters."""
    docs = await document_service.list_documents(
        db, user.id, status=document_status, classification=classification, urgency=urgency
    )
    return {"documents": docs, "total": len(docs)}


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Get document detail."""
    doc = await document_service.get_document(db, user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch("/{document_id}")
async def update_document(
    document_id: uuid.UUID,
    data: DocumentStatusUpdate,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Update document status."""
    doc = await document_service.update_document_status(
        db, user.id, document_id, data.model_dump()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document."""
    deleted = await document_service.delete_document(db, user.id, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return None
