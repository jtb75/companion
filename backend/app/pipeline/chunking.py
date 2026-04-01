"""Document chunking for RAG embedding pipeline."""

import json
import re

from app.config import settings


def chunk_document(
    classification: str,
    ocr_text: str | None,
    spoken_summary: str | None,
    card_summary: str | None,
    extracted_fields: dict | None,
) -> list[dict]:
    """Split document content into chunks for embedding.

    Returns a list of dicts with chunk_text, source_field, chunk_index.
    """
    if classification == "junk":
        return []

    chunks: list[dict] = []
    idx = 0

    # OCR text: split into ~800-char chunks with 100-char overlap
    if ocr_text and ocr_text.strip():
        for text_chunk in _split_text(
            ocr_text,
            max_chars=settings.rag_chunk_size,
            overlap=settings.rag_chunk_overlap,
        ):
            chunks.append({
                "chunk_text": text_chunk,
                "source_field": "ocr_text",
                "chunk_index": idx,
            })
            idx += 1

    # Spoken summary: single chunk
    if spoken_summary and spoken_summary.strip():
        chunks.append({
            "chunk_text": spoken_summary.strip(),
            "source_field": "spoken_summary",
            "chunk_index": idx,
        })
        idx += 1

    # Card summary: single chunk
    if card_summary and card_summary.strip():
        chunks.append({
            "chunk_text": card_summary.strip(),
            "source_field": "card_summary",
            "chunk_index": idx,
        })
        idx += 1

    # Extracted fields: serialize to natural language
    if extracted_fields:
        nl = _fields_to_natural_language(extracted_fields)
        if nl:
            chunks.append({
                "chunk_text": nl,
                "source_field": "extracted_fields",
                "chunk_index": idx,
            })
            idx += 1

    return chunks


def _split_text(
    text: str, max_chars: int = 800, overlap: int = 100
) -> list[str]:
    """Split text at paragraph/sentence boundaries."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Try paragraph boundary first
        segment = text[start:end]
        para_break = segment.rfind("\n\n")
        if para_break > max_chars // 2:
            end = start + para_break + 2
        else:
            # Try sentence boundary
            sentence_match = list(
                re.finditer(r'[.!?]\s+', segment)
            )
            if sentence_match:
                last = sentence_match[-1]
                if last.end() > max_chars // 2:
                    end = start + last.end()

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move forward with overlap
        start = max(end - overlap, start + 1)

    return chunks


def _fields_to_natural_language(fields: dict) -> str:
    """Convert extracted fields dict to a readable string."""
    lines = []
    for key, value in fields.items():
        if value is None:
            continue
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            value = json.dumps(value)
        lines.append(f"{label}: {value}")
    return "; ".join(lines) if lines else ""
