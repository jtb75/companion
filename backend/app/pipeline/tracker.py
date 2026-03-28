"""Stage 6 — Logs questions and checks escalation thresholds."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import QuestionContextType, QuestionStatus, UrgencyLevel
from app.models.question_tracker import QuestionTracker
from app.pipeline.schemas import ClassificationResult, ExtractionResult

# Escalation thresholds from the spec (hours)
ESCALATION_THRESHOLDS: dict[str, int | None] = {
    "routine": None,  # no escalation
    "needs_attention": 24,
    "act_today": 4,
    "urgent": 4,
}


async def create_questions(
    db: AsyncSession,
    user_id: UUID,
    classification: ClassificationResult,
    extraction: ExtractionResult,
) -> list[QuestionTracker]:
    """Create question tracker entries for missing fields or items needing user input."""

    questions: list[QuestionTracker] = []

    if not extraction.missing_fields and not extraction.needs_user_input:
        return questions

    # Map classification to context type
    context_type_map = {
        "bill": QuestionContextType.BILL,
        "medical": QuestionContextType.MEDICATION,
        "legal": QuestionContextType.DOCUMENT,
        "government": QuestionContextType.DOCUMENT,
        "insurance": QuestionContextType.DOCUMENT,
        "form": QuestionContextType.FORM,
    }
    context_type = context_type_map.get(
        classification.classification, QuestionContextType.DOCUMENT
    )

    urgency_map = {
        "routine": UrgencyLevel.ROUTINE,
        "needs_attention": UrgencyLevel.NEEDS_ATTENTION,
        "act_today": UrgencyLevel.ACT_TODAY,
        "urgent": UrgencyLevel.URGENT,
    }
    urgency = urgency_map.get(
        classification.urgency_level, UrgencyLevel.ROUTINE
    )

    threshold = ESCALATION_THRESHOLDS.get(
        classification.urgency_level, 24
    )

    for field in extraction.missing_fields:
        question_text = _generate_question(
            classification.classification, field
        )
        q = QuestionTracker(
            user_id=user_id,
            question_text=question_text,
            context_type=context_type,
            context_ref_id=classification.document_id,
            urgency_level=urgency,
            escalation_threshold_hours=threshold or 24,
            status=QuestionStatus.OPEN,
        )
        db.add(q)
        questions.append(q)

    if questions:
        await db.flush()

    return questions


def _generate_question(classification: str, field: str) -> str:
    """Generate a plain-language question for a missing field."""
    questions = {
        ("bill", "amount_due"): (
            "I couldn't find the amount on this bill."
            " Can you tell me how much it is?"
        ),
        ("bill", "due_date"): (
            "I'm not sure when this bill is due."
            " Do you know the due date?"
        ),
        ("bill", "sender"): (
            "I couldn't tell who this bill is from."
            " Can we look at it together?"
        ),
        ("medical", "provider"): (
            "I see a medical document but I'm not sure"
            " which doctor it's from. Can you help?"
        ),
        ("medical", "date_time"): (
            "I found a medical document but couldn't find"
            " the appointment date. When is it?"
        ),
        ("legal", "sender"): (
            "This looks like a legal document but I"
            " couldn't identify who sent it."
            " Can we check together?"
        ),
        ("legal", "response_deadline"): (
            "This legal notice may have a deadline."
            " Can we look at it to make sure"
            " we don't miss it?"
        ),
    }

    key = (classification, field)
    fallback = (
        f"I need help understanding the"
        f" {field.replace('_', ' ')} on this document."
        f" Can we look at it together?"
    )
    return questions.get(key, fallback)
