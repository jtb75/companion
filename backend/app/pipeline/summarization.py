"""Stage 4 — Generates plain-language summaries. Stubbed (will use LLM in production)."""

from app.pipeline.schemas import (
    ClassificationResult,
    ExtractionResult,
    SummarizationResult,
)


async def summarize(
    classification: ClassificationResult,
    extraction: ExtractionResult,
) -> SummarizationResult:
    """Generate plain-language spoken and card summaries.

    In production, this sends extracted fields to the LLM with summarization
    prompts tuned for 4th-6th grade reading level. Currently uses templates.
    """

    summarizer = SUMMARIZERS.get(
        classification.classification, _summarize_generic
    )
    spoken, card = await summarizer(extraction.extracted_fields, classification)

    # Map internal urgency to user-facing label
    urgency_label = {
        "routine": "Can Wait",
        "needs_attention": "Soon",
        "act_today": "Today",
        "urgent": "Today",
    }.get(classification.urgency_level, "Soon")

    return SummarizationResult(
        document_id=classification.document_id,
        spoken_summary=spoken,
        card_summary=card,
        urgency_label=urgency_label,
    )


async def _summarize_bill(fields: dict, classification: ClassificationResult) -> tuple[str, str]:
    """Generate bill summary."""
    sender = fields.get("sender", "Unknown sender")
    amount = fields.get("amount_due")
    due_date = fields.get("due_date")

    if amount and due_date:
        spoken = f"This is a bill from {sender}. You owe ${amount} and it's due {due_date}."
        card = f"{sender} — ${amount} due {due_date}"
    elif amount:
        spoken = f"This is a bill from {sender}. You owe ${amount}."
        card = f"{sender} — ${amount}"
    else:
        spoken = f"This looks like a bill from {sender}. I couldn't find the amount."
        card = f"{sender} — amount unclear"

    return spoken, card


async def _summarize_medical(fields: dict, classification: ClassificationResult) -> tuple[str, str]:
    """Generate medical document summary."""
    provider = fields.get("provider", "your doctor")
    date_time = fields.get("date_time")

    if date_time:
        spoken = f"You have an appointment with {provider} on {date_time}."
        card = f"{provider} — {date_time}"
    else:
        spoken = f"This is a medical document from {provider}."
        card = f"{provider} — medical document"

    return spoken, card


async def _summarize_legal(fields: dict, classification: ClassificationResult) -> tuple[str, str]:
    """Generate legal document summary — calm but honest."""
    sender = fields.get("sender", "Unknown")
    deadline = fields.get("response_deadline")

    spoken = f"This is a serious letter from {sender}."
    if deadline:
        spoken += f" It has a deadline of {deadline}."
    spoken += " You should not handle this alone — want me to let your trusted contact know?"

    card = f"Legal notice from {sender}"
    if deadline:
        card += f" — respond by {deadline}"

    return spoken, card


async def _summarize_junk(fields: dict, classification: ClassificationResult) -> tuple[str, str]:
    """Briefly dismiss junk mail."""
    return "This is junk mail. I'll set it aside.", "Junk mail — no action needed"


async def _summarize_generic(fields: dict, classification: ClassificationResult) -> tuple[str, str]:
    """Fallback summary."""
    preview = fields.get("raw_text_preview", "")[:100]
    if classification.confidence_score < 0.6:
        spoken = (
            "I'm not completely sure what this is."
            " It could be important."
            " Want to look at it together?"
        )
        card = "Unknown document — needs review"
    else:
        spoken = f"I received a document. Here's what it says: {preview}"
        card = "Document received"

    return spoken, card


SUMMARIZERS: dict[str, object] = {
    "bill": _summarize_bill,
    "medical": _summarize_medical,
    "legal": _summarize_legal,
    "junk": _summarize_junk,
}
