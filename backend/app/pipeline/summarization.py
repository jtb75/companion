"""Stage 4 — Generates plain-language summaries using LLM.

Uses Gemini to create spoken and card summaries at a 4th-6th grade reading level.
Prompts are configurable via Admin -> Prompts (system_config).
Falls back to templates if LLM is unavailable.
"""

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig
from app.pipeline.schemas import (
    ClassificationResult,
    ExtractionResult,
    SummarizationResult,
)
from app.pipeline.text_complexity import get_flesch_kincaid_grade

logger = logging.getLogger(__name__)

_DEFAULT_SUMMARIZATION_PROMPT = (
    "You are a compassionate independence assistant for adults with developmental disabilities.\n"
    "Your goal is to summarize documents using the 'Easy Read' philosophy: "
    "simple words, clear actions, and no jargon.\n\n"
    "## INPUT DATA\n"
    "Classification: {classification}\n"
    "Urgency: {urgency}\n"
    "Extracted Data: {fields_json}\n\n"
    "## GUIDELINES\n"
    "- Reading Level: 4th-6th grade.\n"
    "- Tone: Warm, helpful, and reassuring.\n"
    "- Structure: 'What it is' followed by 'What to do'.\n"
    "- Safety: If the document is about money owed or medical news, "
    "stay calm and suggest a small next step.\n\n"
    "## TASK\n"
    "1. Internal Reasoning: Briefly analyze the importance of this document.\n"
    "2. Spoken Summary: A 2-3 sentence friendly explanation for the user.\n"
    "3. Card Summary: A dashboard line (max 60 chars) in the format 'Sender — Key Detail'.\n\n"
    "## OUTPUT FORMAT\n"
    "Return ONLY valid JSON with these keys: 'reasoning', 'spoken', 'card'.\n"
    "Example:\n"
    '{{'
    '  "reasoning": "This is a utility bill with a clear due date.",'
    '  "spoken": "You have a bill from the Electric Company '
    'for $45. You should pay it by next Friday.",'
    '  "card": "Electric Co — $45 due Friday"'
    '}}'
)


async def _get_summarization_prompt(db: AsyncSession | None) -> str:
    """Load summarization prompt from system_config, falling back to default."""
    if db is not None:
        try:
            async with db.begin_nested():
                result = await db.execute(
                    select(SystemConfig).where(
                        SystemConfig.category == "summarization_prompt",
                        SystemConfig.key == "default",
                        SystemConfig.is_active.is_(True),
                    )
                )
                config = result.scalar_one_or_none()
                if config and config.value and config.value.get("prompt"):
                    return config.value["prompt"]
        except Exception:
            logger.warning(
                "Failed to load summarization prompt, using default"
            )
    return _DEFAULT_SUMMARIZATION_PROMPT


async def summarize(
    classification: ClassificationResult,
    extraction: ExtractionResult,
    db: AsyncSession | None = None,
) -> SummarizationResult:
    """Generate plain-language spoken and card summaries."""

    # Try LLM summarization
    llm_result = await _llm_summarize(
        classification, extraction, db
    )
    if llm_result is not None:
        spoken, card, reasoning = llm_result
    else:
        # Fallback to templates
        logger.warning(
            "LLM summarization failed for doc %s, using templates",
            classification.document_id,
        )
        summarizer = TEMPLATE_SUMMARIZERS.get(
            classification.classification, _template_generic
        )
        spoken, card = await summarizer(
            extraction.extracted_fields, classification
        )
        reasoning = "Fallback template used (LLM unavailable or failed)."

    urgency_label = {
        "routine": "Can Wait",
        "needs_attention": "Soon",
        "act_today": "Today",
        "urgent": "Today",
    }.get(classification.urgency_level, "Soon")

    # Reading complexity check
    grade = get_flesch_kincaid_grade(spoken)
    if grade > 6.0:
        logger.warning(
            "COMPLEX_TEXT_WARNING: doc=%s grade=%.1f summary=%s",
            classification.document_id, grade, spoken
        )

    return SummarizationResult(
        document_id=classification.document_id,
        spoken_summary=spoken,
        card_summary=card,
        urgency_label=urgency_label,
        reasoning=reasoning,
        reading_grade=grade,
    )


async def _llm_summarize(
    classification: ClassificationResult,
    extraction: ExtractionResult,
    db: AsyncSession | None,
) -> tuple[str, str, str] | None:
    """Use Gemini to generate summaries."""
    try:
        from app.conversation.llm import get_llm_client

        llm = get_llm_client()
        prompt_template = await _get_summarization_prompt(db)

        fields_json = json.dumps(
            extraction.extracted_fields, indent=2, default=str
        )
        prompt = prompt_template.format(
            classification=classification.classification,
            urgency=classification.urgency_level,
            fields_json=fields_json,
        )

        response = await llm.generate(
            system_prompt=(
                "You are a friendly document summarizer. "
                "Return ONLY valid JSON, no other text."
            ),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )

        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        parsed = json.loads(cleaned)
        reasoning = parsed.get("reasoning", "").strip()
        spoken = parsed.get("spoken", "").strip()
        card = parsed.get("card", "").strip()

        if spoken and card:
            logger.info(
                "LLM_SUMMARIZE_REASONING: doc=%s reasoning=%s",
                classification.document_id, reasoning
            )
            return spoken, card, reasoning

        logger.warning("LLM summarization returned empty fields")
        return None
    except json.JSONDecodeError as e:
        logger.warning("LLM summarization JSON parse failed: %s", e)
        return None
    except Exception:
        logger.exception("LLM summarization failed")
        return None


# ── Template fallbacks ──


async def _template_bill(
    fields: dict, classification: ClassificationResult
) -> tuple[str, str]:
    sender = fields.get("sender", "Unknown sender")
    amount = fields.get("amount_due")
    due_date = fields.get("due_date")

    if amount and due_date:
        spoken = (
            f"This is a bill from {sender}. "
            f"You owe ${amount} and it's due {due_date}."
        )
        card = f"{sender} — ${amount} due {due_date}"
    elif amount:
        spoken = f"This is a bill from {sender}. You owe ${amount}."
        card = f"{sender} — ${amount}"
    else:
        spoken = (
            f"This looks like a bill from {sender}. "
            "I couldn't find the amount."
        )
        card = f"{sender} — amount unclear"

    return spoken, card


async def _template_medical(
    fields: dict, classification: ClassificationResult
) -> tuple[str, str]:
    provider = fields.get("provider", "your doctor")
    date_time = fields.get("date_time")

    if date_time:
        spoken = (
            f"You have an appointment with {provider} on {date_time}."
        )
        card = f"{provider} — {date_time}"
    else:
        spoken = f"This is a medical document from {provider}."
        card = f"{provider} — medical document"

    return spoken, card


async def _template_legal(
    fields: dict, classification: ClassificationResult
) -> tuple[str, str]:
    sender = fields.get("sender", "Unknown")
    deadline = fields.get("response_deadline")

    spoken = f"This is a serious letter from {sender}."
    if deadline:
        spoken += f" It has a deadline of {deadline}."
    spoken += (
        " You should not handle this alone — "
        "want me to let your trusted contact know?"
    )

    card = f"Legal notice from {sender}"
    if deadline:
        card += f" — respond by {deadline}"

    return spoken, card


async def _template_junk(
    fields: dict, classification: ClassificationResult
) -> tuple[str, str]:
    return (
        "This is junk mail. I'll set it aside.",
        "Junk mail — no action needed",
    )


async def _template_generic(
    fields: dict, classification: ClassificationResult
) -> tuple[str, str]:
    preview = fields.get("raw_text_preview", "")[:100]
    if classification.confidence_score < 0.6:
        spoken = (
            "I'm not completely sure what this is. "
            "It could be important. "
            "Want to look at it together?"
        )
        card = "Unknown document — needs review"
    else:
        spoken = (
            f"I received a document. Here's what it says: {preview}"
        )
        card = "Document received"

    return spoken, card


TEMPLATE_SUMMARIZERS: dict[str, object] = {
    "bill": _template_bill,
    "medical": _template_medical,
    "legal": _template_legal,
    "junk": _template_junk,
}
