"""Stage 3 — Extracts structured fields per document type using LLM.

Uses Gemini to extract structured JSON from OCR text.
Prompts are configurable via Admin -> Prompts (system_config).
Falls back to regex if LLM is unavailable.
"""

import json
import logging
import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig
from app.pipeline.schemas import (
    BillExtraction,
    ClassificationResult,
    ExtractionResult,
    LegalExtraction,
    MedicalAppointmentExtraction,
    NormalizedDocument,
)

logger = logging.getLogger(__name__)

# ── Default prompts (overridable via Admin → Prompts) ──

_DEFAULT_BILL_PROMPT = """Extract the following fields from this bill/statement document.
Return ONLY valid JSON with these exact keys:

{
  "sender": "The company or organization that sent the bill (full name)",
  "amount_due": "The total amount due as a number (e.g. 51.24)",
  "due_date": "Payment due date in MM/DD/YYYY format",
  "account_number_masked": "Account number with all but last 4 digits masked (e.g. ****0666)"
}

If a field cannot be found, set its value to null.
Do NOT include any text outside the JSON object.

Document text:
"""

_DEFAULT_MEDICAL_PROMPT = """Extract the following fields from this medical document.
Return ONLY valid JSON with these exact keys:

{
  "provider": "The doctor or healthcare provider's full name and title",
  "date_time": "Appointment date/time in MM/DD/YYYY format",
  "location": "Office or facility name and address if available",
  "preparation_instructions": "Any preparation instructions for the patient"
}

If a field cannot be found, set its value to null.
Do NOT include any text outside the JSON object.

Document text:
"""

_DEFAULT_LEGAL_PROMPT = """Extract the following fields from this legal document.
Return ONLY valid JSON with these exact keys:

{
  "sender": "The organization, law firm, or agency that sent the document",
  "response_deadline": "Any deadline to respond in MM/DD/YYYY format",
  "action_required": "Brief description of what action is required"
}

If a field cannot be found, set its value to null.
Do NOT include any text outside the JSON object.

Document text:
"""

_DEFAULT_GENERIC_PROMPT = """Extract key information from this document.
Return ONLY valid JSON with these keys:

{
  "sender": "Who sent this document",
  "summary": "One-sentence summary of what this document is about",
  "action_required": "Any action the recipient needs to take"
}

If a field cannot be found, set its value to null.
Do NOT include any text outside the JSON object.

Document text:
"""

DEFAULT_PROMPTS: dict[str, str] = {
    "bill": _DEFAULT_BILL_PROMPT,
    "medical": _DEFAULT_MEDICAL_PROMPT,
    "legal": _DEFAULT_LEGAL_PROMPT,
    "generic": _DEFAULT_GENERIC_PROMPT,
}


async def _get_extraction_prompt(
    db: AsyncSession | None, classification: str
) -> str:
    """Load extraction prompt from system_config, falling back to defaults."""
    if db is not None:
        try:
            result = await db.execute(
                select(SystemConfig).where(
                    SystemConfig.category == "extraction_prompt",
                    SystemConfig.key == classification,
                    SystemConfig.is_active.is_(True),
                )
            )
            config = result.scalar_one_or_none()
            if config and config.value and config.value.get("prompt"):
                return config.value["prompt"]
        except Exception:
            logger.warning(
                "Failed to load extraction prompt for %s, using default",
                classification,
            )
            await db.rollback()
    return DEFAULT_PROMPTS.get(classification, DEFAULT_PROMPTS["generic"])


async def extract(
    doc: NormalizedDocument,
    classification: ClassificationResult,
    db: AsyncSession | None = None,
) -> ExtractionResult:
    """Extract structured fields using LLM, with regex fallback."""

    text = doc.raw_text
    doc_type = classification.classification

    # Try LLM extraction first
    llm_fields = await _llm_extract(text, doc_type, db)
    if llm_fields is not None:
        fields, missing = _validate_fields(llm_fields, doc_type)
        logger.info(
            "LLM extraction for doc %s: %d fields, %d missing",
            doc.document_id, len(fields), len(missing),
        )
        return ExtractionResult(
            document_id=doc.document_id,
            extracted_fields=fields,
            missing_fields=missing,
            needs_user_input=len(missing) > 0,
        )

    # Fallback to regex
    logger.warning(
        "LLM extraction failed for doc %s, falling back to regex",
        doc.document_id,
    )
    extractor = REGEX_EXTRACTORS.get(doc_type, _regex_generic)
    fields, missing = await extractor(text)

    return ExtractionResult(
        document_id=doc.document_id,
        extracted_fields=fields,
        missing_fields=missing,
        needs_user_input=len(missing) > 0,
    )


async def _llm_extract(
    text: str, doc_type: str, db: AsyncSession | None
) -> dict | None:
    """Use Gemini to extract structured fields from document text."""
    try:
        from app.conversation.llm import get_llm_client

        llm = get_llm_client()
        prompt = await _get_extraction_prompt(db, doc_type)
        text_snippet = text[:4000]  # Limit to avoid token overflow

        response = await llm.generate(
            system_prompt=(
                "You are a document data extractor. "
                "Return ONLY valid JSON, no other text."
            ),
            messages=[
                {"role": "user", "content": prompt + text_snippet}
            ],
            max_tokens=500,
        )

        # Strip markdown code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(
                r"^```(?:json)?\s*", "", cleaned
            )
            cleaned = re.sub(r"\s*```$", "", cleaned)

        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed

        logger.warning("LLM extraction returned non-dict: %s", type(parsed))
        return None
    except json.JSONDecodeError as e:
        logger.warning("LLM extraction JSON parse failed: %s", e)
        return None
    except Exception:
        logger.exception("LLM extraction failed")
        return None


def _validate_fields(
    fields: dict, doc_type: str
) -> tuple[dict, list[str]]:
    """Validate extracted fields and identify missing ones."""
    missing: list[str] = []

    if doc_type == "bill":
        required = ["sender", "amount_due", "due_date"]
        # Clean up amount_due — ensure it's a number
        if fields.get("amount_due") is not None:
            try:
                fields["amount_due"] = float(
                    str(fields["amount_due"])
                    .replace("$", "")
                    .replace(",", "")
                )
            except (ValueError, TypeError):
                fields["amount_due"] = None

        for key in required:
            if not fields.get(key):
                missing.append(key)

    elif doc_type == "medical":
        required = ["provider"]
        for key in required:
            if not fields.get(key):
                missing.append(key)

    elif doc_type == "legal":
        required = ["sender"]
        for key in required:
            if not fields.get(key):
                missing.append(key)

    # Remove null values for cleaner storage
    fields = {k: v for k, v in fields.items() if v is not None}

    return fields, missing


# ── Regex fallback extractors (kept for resilience) ──


async def _regex_bill(text: str) -> tuple[dict, list[str]]:
    """Regex fallback for bill extraction."""
    missing: list[str] = []

    amount_match = re.search(r"\$\s*([\d,]+\.?\d*)", text)
    amount = (
        Decimal(amount_match.group(1).replace(",", ""))
        if amount_match
        else None
    )
    if not amount:
        missing.append("amount_due")

    date_match = re.search(
        r"(?:due|by|before)\s+(?:date:?\s*)?("
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|\w+ \d{1,2},? \d{4})",
        text,
        re.IGNORECASE,
    )
    due_date = date_match.group(1) if date_match else None
    if not due_date:
        missing.append("due_date")

    acct_match = re.search(
        r"(?:account|acct)[\s#:]*(\d{4,})", text, re.IGNORECASE
    )
    acct_masked = (
        f"****{acct_match.group(1)[-4:]}" if acct_match else None
    )

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


async def _regex_medical(text: str) -> tuple[dict, list[str]]:
    """Regex fallback for medical extraction."""
    missing: list[str] = []

    provider_match = re.search(
        r"(?:Dr\.?|Doctor)\s+(\w+(?:\s+\w+)?)",
        text,
        re.IGNORECASE,
    )
    provider = provider_match.group(0) if provider_match else None
    if not provider:
        missing.append("provider")

    date_match = re.search(
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
        r"\s*(?:at\s+)?(\d{1,2}:\d{2}\s*(?:am|pm)?)?",
        text,
        re.IGNORECASE,
    )
    date_time = date_match.group(0) if date_match else None
    if not date_time:
        missing.append("date_time")

    fields = MedicalAppointmentExtraction(
        provider=provider,
        date_time=date_time,
    ).model_dump(exclude_none=False)

    return fields, missing


async def _regex_legal(text: str) -> tuple[dict, list[str]]:
    """Regex fallback for legal extraction."""
    missing: list[str] = []

    sender = _extract_sender(text)
    if not sender:
        missing.append("sender")

    deadline_match = re.search(
        r"(?:respond|reply|action)\s+(?:by|before|within)"
        r"\s+([\w\s,]+\d{4}|\d+ days)",
        text,
        re.IGNORECASE,
    )
    deadline = (
        deadline_match.group(1).strip() if deadline_match else None
    )
    if not deadline:
        missing.append("response_deadline")

    fields = LegalExtraction(
        sender=sender,
        response_deadline=deadline,
    ).model_dump(exclude_none=False)

    return fields, missing


async def _regex_generic(text: str) -> tuple[dict, list[str]]:
    """Fallback extraction for unrecognized types."""
    return {"raw_text_preview": text[:200]}, []


def _extract_sender(text: str) -> str | None:
    """Try to extract sender/organization from text."""
    from_match = re.search(
        r"(?:from|sent by):?\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )
    if from_match:
        return from_match.group(1).strip()
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line) > 3:
            return line[:100]
    return None


REGEX_EXTRACTORS: dict[str, object] = {
    "bill": _regex_bill,
    "medical": _regex_medical,
    "legal": _regex_legal,
}
