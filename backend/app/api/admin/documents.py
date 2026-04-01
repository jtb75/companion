"""Admin API — Document management and pipeline tracking."""

import logging
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AdminUser, require_admin_role
from app.db import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/documents",
    tags=["Admin - Documents"],
)

_editor = require_admin_role("editor")


@router.get("")
async def list_documents(
    status: DocumentStatus | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """List all documents with pagination."""
    base = (
        select(
            Document.id,
            User.preferred_name.label("user_name"),
            User.email.label("user_email"),
            Document.source_channel,
            Document.status,
            Document.classification,
            Document.urgency_level,
            Document.card_summary,
            Document.received_at,
            Document.processed_at,
        )
        .join(User, Document.user_id == User.id)
        .order_by(Document.received_at.desc())
    )
    count_q = select(func.count()).select_from(Document)

    if status is not None:
        base = base.where(Document.status == status)
        count_q = count_q.where(Document.status == status)

    rows = await db.execute(base.limit(limit).offset(offset))
    total = await db.scalar(count_q)

    items = []
    for row in rows:
        items.append({
            "document_id": str(row.id),
            "user_name": row.user_name,
            "user_email": row.user_email,
            "source_channel": (
                row.source_channel.value
                if row.source_channel
                else None
            ),
            "status": (
                row.status.value if row.status else None
            ),
            "classification": (
                row.classification.value
                if row.classification
                else None
            ),
            "urgency": (
                row.urgency_level.value
                if row.urgency_level
                else None
            ),
            "card_summary": row.card_summary,
            "created_at": (
                row.received_at.isoformat()
                if row.received_at
                else None
            ),
            "processed_at": (
                row.processed_at.isoformat()
                if row.processed_at
                else None
            ),
        })

    return {
        "documents": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{document_id}/cancel")
async def cancel_document(
    document_id: uuid.UUID,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a document by setting its status to FAILED."""
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(
            status_code=404, detail="Document not found"
        )
    doc.status = DocumentStatus.FAILED
    await db.commit()
    logger.info(
        "Document %s cancelled by admin %s",
        document_id,
        admin.email,
    )
    return {"document_id": str(document_id), "status": "failed"}


@router.post("/{document_id}/resubmit")
async def resubmit_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Reset a document to RECEIVED and re-trigger the pipeline."""
    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(
            status_code=404, detail="Document not found"
        )
    doc.status = DocumentStatus.RECEIVED
    await db.commit()

    async def _run_pipeline(
        doc_id: uuid.UUID, user_id: uuid.UUID
    ):
        from app.db.session import async_session_factory
        from app.pipeline.orchestrator import process_document

        async with async_session_factory() as session:
            try:
                await process_document(
                    session, doc_id, user_id
                )
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception(
                    "Resubmit pipeline failed for %s",
                    doc_id,
                )

    background_tasks.add_task(
        _run_pipeline, doc.id, doc.user_id
    )
    logger.info(
        "Document %s resubmitted by admin %s",
        document_id,
        admin.email,
    )
    return {
        "document_id": str(document_id),
        "status": "resubmitted",
    }
