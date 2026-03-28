"""Stage 3 — Extracts structured fields per document type. Stubbed with regex patterns."""

import re
from decimal import Decimal

from app.pipeline.schemas import (
    BillExtraction,
    ClassificationResult,
    ExtractionResult,
    LegalExtraction,
    MedicalAppointmentExtraction,
    NormalizedDocument,
)


async def extract(
    doc: NormalizedDocument, classification: ClassificationResult
) -> ExtractionResult:
    """Extract structured fields based on document classification."""

    extractor = EXTRACTORS.get(classification.classification, _extract_generic)
    fields, missing = await extractor(doc.raw_text)

    return ExtractionResult(
        document_id=doc.document_id,
        extracted_fields=fields,
        missing_fields=missing,
        needs_user_input=len(missing) > 0,
    )


async def _extract_bill(text: str) -> tuple[dict, list[str]]:
    """Extract bill-specific fields."""
    missing: list[str] = []

    # Amount
    amount_match = re.search(r"\$\s*([\d,]+\.?\d*)", text)
    amount = Decimal(amount_match.group(1).replace(",", "")) if amount_match else None
    if not amount:
        missing.append("amount_due")

    # Due date (various formats)
    date_match = re.search(
        r"(?:due|by|before)\s+(?:date:?\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4})",
        text, re.IGNORECASE,
    )
    due_date = date_match.group(1) if date_match else None
    if not due_date:
        missing.append("due_date")

    # Account number (mask to last 4)
    acct_match = re.search(r"(?:account|acct)[\s#:]*(\d{4,})", text, re.IGNORECASE)
    acct_masked = f"****{acct_match.group(1)[-4:]}" if acct_match else None

    # Sender (first capitalized entity or line)
    sender = _extract_sender(text)
    if not sender:
        missing.append("sender")

    fields = BillExtraction(
        sender=sender,
        account_number_masked=acct_masked,
        amount_due=amount,
        due_date=due_date,
    ).model_dump(exclude_none=False)

    return fields, missing


async def _extract_medical(text: str) -> tuple[dict, list[str]]:
    """Extract medical appointment fields."""
    missing: list[str] = []

    provider_match = re.search(r"(?:Dr\.?|Doctor)\s+(\w+(?:\s+\w+)?)", text, re.IGNORECASE)
    provider = provider_match.group(0) if provider_match else None
    if not provider:
        missing.append("provider")

    date_match = re.search(
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*(?:at\s+)?(\d{1,2}:\d{2}\s*(?:am|pm)?)?",
        text, re.IGNORECASE,
    )
    date_time = date_match.group(0) if date_match else None
    if not date_time:
        missing.append("date_time")

    fields = MedicalAppointmentExtraction(
        provider=provider,
        date_time=date_time,
    ).model_dump(exclude_none=False)

    return fields, missing


async def _extract_legal(text: str) -> tuple[dict, list[str]]:
    """Extract legal notice fields."""
    missing: list[str] = []

    sender = _extract_sender(text)
    if not sender:
        missing.append("sender")

    deadline_match = re.search(
        r"(?:respond|reply|action)\s+(?:by|before|within)\s+([\w\s,]+\d{4}|\d+ days)",
        text, re.IGNORECASE,
    )
    deadline = deadline_match.group(1).strip() if deadline_match else None
    if not deadline:
        missing.append("response_deadline")

    fields = LegalExtraction(
        sender=sender,
        response_deadline=deadline,
    ).model_dump(exclude_none=False)

    return fields, missing


async def _extract_generic(text: str) -> tuple[dict, list[str]]:
    """Fallback extraction for unrecognized types."""
    return {"raw_text_preview": text[:200]}, []


def _extract_sender(text: str) -> str | None:
    """Try to extract sender/organization from text."""
    # Look for common patterns
    from_match = re.search(r"(?:from|sent by):?\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if from_match:
        return from_match.group(1).strip()
    # First non-empty line as fallback
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line) > 3:
            return line[:100]
    return None


EXTRACTORS: dict[str, object] = {
    "bill": _extract_bill,
    "medical": _extract_medical,
    "legal": _extract_legal,
    # Others fall back to generic
}
