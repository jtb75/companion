"""Admin API — Document management and pipeline tracking."""

import logging
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AdminUser, require_admin_role
from app.db import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.pipeline_metrics import PipelineMetric
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

    result = await db.execute(
        base.limit(limit).offset(offset)
    )
    rows = result.all()
    total = await db.scalar(count_q)

    # Collect document IDs for pipeline metrics query
    doc_ids = [row.id for row in rows]

    # Fetch pipeline metrics for all documents
    stage_map: dict[str, list] = {}
    if doc_ids:
        metrics_q = await db.execute(
            select(PipelineMetric)
            .where(PipelineMetric.document_id.in_(doc_ids))
            .order_by(PipelineMetric.recorded_at)
        )
        for m in metrics_q.scalars().all():
            did = str(m.document_id)
            if did not in stage_map:
                stage_map[did] = []
            stage_map[did].append({
                "stage": m.stage.capitalize(),
                "status": "completed" if m.status == "completed" else "failed",
                "duration_ms": m.duration_ms,
            })

    items = []
    for row in rows:
        did = str(row.id)
        items.append({
            "id": did,
            "user_name": row.user_name,
            "user_email": row.user_email,
            "source_channel": (
                row.source_channel.value
                if row.source_channel
                else None
            ),
            "status": (
                row.status.value
                if row.status
                else None
            ),
            "classification": (
                row.classification.value
                if row.classification
                else None
            ),
            "urgency_level": (
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
            "pipeline_stages": stage_map.get(did, []),
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
    admin: AdminUser = Depends(_editor),
    db: AsyncSession = Depends(get_db),
):
    """Reset a document to RECEIVED and re-trigger the pipeline."""
    from app.events.publisher import event_publisher
    from app.events.schemas import DocumentReceivedPayload

    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(
            status_code=404, detail="Document not found"
        )
    # Clear previous pipeline metrics and pending reviews
    await db.execute(
        delete(PipelineMetric).where(
            PipelineMetric.document_id == document_id
        )
    )
    from app.models.pending_review import PendingReview
    await db.execute(
        delete(PendingReview).where(
            PendingReview.document_id == document_id
        )
    )
    doc.status = DocumentStatus.RECEIVED
    doc.classification = None
    doc.confidence_score = None
    doc.urgency_level = None
    doc.extracted_fields = None
    doc.spoken_summary = None
    doc.card_summary = None
    doc.routing_destination = None
    doc.processed_at = None
    
    # Save resets
    await db.commit()

    # Trigger pipeline via event
    await event_publisher.publish(
        "document.received",
        user_id=doc.user_id,
        payload=DocumentReceivedPayload(
            document_id=doc.id,
            source_channel=getattr(
                doc.source_channel, "value",
                str(doc.source_channel),
            ),
        ),
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
