"""Embedding service — generates vector embeddings for document chunks."""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.pipeline.chunking import chunk_document
from app.pipeline.schemas import (
    ClassificationResult,
    ExtractionResult,
    SummarizationResult,
)

logger = logging.getLogger(__name__)


async def embed_document(
    db: AsyncSession,
    document_id: UUID,
    user_id: UUID,
    classification_result: ClassificationResult,
    extraction_result: ExtractionResult,
    summarization_result: SummarizationResult,
) -> int:
    """Generate embeddings for a document's chunks.

    Returns the number of chunks embedded.
    """
    # Get OCR text from the document's source_metadata
    doc = await db.get(Document, document_id)
    ocr_text = ""
    if doc and doc.source_metadata:
        ocr_text = doc.source_metadata.get("ocr_text", "")
    if not ocr_text:
        ocr_text = extraction_result.extracted_fields.get(
            "raw_text", ""
        )

    # Build chunks from pipeline results
    chunks = chunk_document(
        classification=classification_result.classification,
        ocr_text=ocr_text,
        spoken_summary=summarization_result.spoken_summary,
        card_summary=summarization_result.card_summary,
        extracted_fields=extraction_result.extracted_fields,
    )

    if not chunks:
        logger.info(
            "No chunks to embed for document %s", document_id
        )
        return 0

    # Delete existing chunks for re-embedding support
    await db.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_id == document_id
        )
    )

    # Get embeddings from Vertex AI
    texts = [c["chunk_text"] for c in chunks]
    embeddings = await _get_embeddings(texts)

    # Insert chunk rows
    for chunk_data, embedding in zip(
        chunks, embeddings, strict=True
    ):
        chunk = DocumentChunk(
            document_id=document_id,
            user_id=user_id,
            chunk_index=chunk_data["chunk_index"],
            chunk_text=chunk_data["chunk_text"],
            token_count=len(chunk_data["chunk_text"]) // 4,
            source_field=chunk_data["source_field"],
            embedding=embedding,
        )
        db.add(chunk)

    await db.flush()
    logger.info(
        "Embedded %d chunks for document %s",
        len(chunks),
        document_id,
    )
    return len(chunks)


async def _get_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """Get embeddings from Vertex AI text-embedding model."""
    import vertexai
    from vertexai.language_models import (
        TextEmbeddingInput,
        TextEmbeddingModel,
    )

    def _sync_embed():
        vertexai.init(
            project=settings.gcp_project_id,
            location=settings.gemini_location,
        )
        model = TextEmbeddingModel.from_pretrained(
            settings.embedding_model
        )
        inputs = [
            TextEmbeddingInput(
                text=t, task_type="RETRIEVAL_DOCUMENT"
            )
            for t in texts
        ]
        result = model.get_embeddings(inputs)
        return [e.values for e in result]

    return await asyncio.to_thread(_sync_embed)
