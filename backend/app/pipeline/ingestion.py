"""Stage 1 — Normalizes camera scan uploads and email content into NormalizedDocument."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.pipeline.schemas import NormalizedDocument


async def process_camera_scan(
    db: AsyncSession, document_id: UUID, image_data: bytes | None = None
) -> NormalizedDocument:
    """Process a camera scan image into normalized text.

    In production: sends image to Google Document AI for OCR.
    In development: uses the raw_text already stored in the document record.
    """
    doc = await db.get(Document, document_id)
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    # In production, this would:
    # 1. Download image from GCS using raw_text_ref
    # 2. Send to Google Document AI
    # 3. Get OCR text back
    # For now, use any text already in the document or the raw_text_ref path
    raw_text = ""
    if doc.source_metadata and isinstance(doc.source_metadata, dict):
        raw_text = doc.source_metadata.get("raw_text", "")
    if not raw_text and doc.raw_text_ref:
        raw_text = doc.raw_text_ref  # may be a GCS path; placeholder for dev

    quality_score = 0.85  # placeholder

    return NormalizedDocument(
        document_id=document_id,
        user_id=doc.user_id,
        source_channel=getattr(
            doc.source_channel, "value", str(doc.source_channel)
        ),
        raw_text=raw_text,
        metadata=doc.source_metadata or {},
        quality_score=quality_score,
    )


async def process_email(
    db: AsyncSession, document_id: UUID, email_content: dict | None = None
) -> NormalizedDocument:
    """Process an email into normalized text."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    raw_text = ""
    if email_content:
        raw_text = email_content.get("body_text", "")
    elif doc.source_metadata and isinstance(doc.source_metadata, dict):
        raw_text = doc.source_metadata.get("body_text", doc.source_metadata.get("raw_text", ""))

    return NormalizedDocument(
        document_id=document_id,
        user_id=doc.user_id,
        source_channel="email",
        raw_text=raw_text,
        metadata=doc.source_metadata or {},
        quality_score=1.0,  # email text is always clean
    )
