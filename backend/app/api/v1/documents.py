"""App API — Document routes."""

import asyncio
import logging
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from google.cloud import storage
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import User, require_complete_profile
from app.config import settings
from app.db import get_db
from app.models.enums import DocumentStatus, SourceChannel
from app.schemas.document import DocumentStatusUpdate
from app.services import document_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_SCAN_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "application/pdf": "pdf",
}
MAX_SCAN_SIZE = 10 * 1024 * 1024  # 10 MB


async def _upload_to_gcs(
    blob_path: str, data: bytes, content_type: str
) -> str:
    """Upload bytes to GCS in a thread (sync client)."""
    def _upload():
        client = storage.Client()
        bucket = client.bucket(settings.gcs_bucket_documents)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{bucket.name}/{blob_path}"

    return await asyncio.to_thread(_upload)


@router.post("/scan", status_code=status.HTTP_201_CREATED)
async def scan_document(
    file: UploadFile = File(...),
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Upload a camera-scanned document for processing."""
    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_SCAN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported file type. "
                "Accepted: JPEG, PNG, HEIC, PDF."
            ),
        )

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_SCAN_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 10 MB limit.",
        )

    # Upload to GCS
    ext = ALLOWED_SCAN_TYPES[content_type]
    file_id = uuid.uuid4()
    blob_path = f"scans/{user.id}/{file_id}.{ext}"
    try:
        gcs_uri = await _upload_to_gcs(
            blob_path, data, content_type
        )
    except Exception:
        logger.exception("GCS upload failed for user %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload file to storage.",
        ) from None

    # Create document record (publishes document.received event)
    doc = await document_service.create_document(
        db,
        user.id,
        {
            "source_channel": SourceChannel.CAMERA_SCAN,
            "status": DocumentStatus.RECEIVED,
            "raw_text_ref": gcs_uri,
            "source_metadata": {
                "original_filename": file.filename,
                "content_type": content_type,
                "size_bytes": len(data),
            },
        },
    )

    # Commit the transaction
    await db.commit()

    return {
        "document_id": doc.id,
        "status": "processing",
    }


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


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: uuid.UUID,
    user: User = Depends(require_complete_profile),
    db: AsyncSession = Depends(get_db),
):
    """Get the current processing status of a document."""
    doc = await document_service.get_document(
        db, user.id, document_id
    )
    if doc is None:
        raise HTTPException(
            status_code=404, detail="Document not found"
        )
    return {
        "document_id": doc.id,
        "status": doc.status,
        "classification": doc.classification,
        "processed_at": doc.processed_at,
    }


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
