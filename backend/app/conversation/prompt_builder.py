from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.branding import BRAND_MID
from app.conversation.persona import DD_PERSONA, DEFAULT_CONSTRAINTS
from app.models.appointment import Appointment
from app.models.bill import Bill
from app.models.functional_memory import FunctionalMemory
from app.models.medication import Medication
from app.models.user import User

logger = logging.getLogger(__name__)


async def build_system_prompt(
    db: AsyncSession,
    user: User,
    session_trigger: str = "user_initiated",
    user_query: str | None = None,
) -> str:
    """Assemble the 6-component system prompt.

    Components:
    1. D.D. persona definition (fixed)
    2. User's functional memory (dynamic)
    3. Session context (dynamic)
    4. RAG document context (dynamic, query-dependent)
    5. Active alerts and pending items (dynamic)
    6. Conversation constraints (fixed)
    """
    parts = []

    # 1. Persona (fixed)
    parts.append(DD_PERSONA)

    # 2. User's functional memory
    memory_context = await _build_memory_context(db, user)
    if memory_context:
        parts.append(
            f"\n--- User Context ---\n{memory_context}"
        )

    # 3. Session context
    session_context = _build_session_context(
        user, session_trigger
    )
    parts.append(
        f"\n--- Session Context ---\n{session_context}"
    )

    # 4. RAG document context
    if user_query:
        doc_context = await _build_document_context(
            db, user.id, user_query
        )
        if doc_context:
            parts.append(
                f"\n--- Document Context ---\n{doc_context}"
            )

    # 5. Active alerts / pending items
    alerts_context = await _build_alerts_context(db, user.id)
    if alerts_context:
        parts.append(
            f"\n--- Active Items ---\n{alerts_context}"
        )

    # 6. Constraints (fixed)
    parts.append(
        f"\n--- Response Rules ---\n{DEFAULT_CONSTRAINTS}"
    )

    return "\n".join(parts)


async def _build_memory_context(db: AsyncSession, user: User) -> str:
    """Build context from user's functional memory."""
    lines = []
    name = user.nickname or user.preferred_name
    lines.append(f"The user's name is {name}.")

    # Fetch memories
    result = await db.execute(
        select(FunctionalMemory)
        .where(FunctionalMemory.user_id == user.id)
        .limit(20)
    )
    memories = result.scalars().all()
    for mem in memories:
        lines.append(f"- {mem.key}: {mem.value}")

    # Medications
    result = await db.execute(
        select(Medication)
        .where(Medication.user_id == user.id, Medication.is_active.is_(True))
    )
    meds = result.scalars().all()
    if meds:
        med_list = ", ".join(
            f"{m.name} ({m.dosage}, {m.frequency})" for m in meds
        )
        lines.append(f"- Medications: {med_list}")

    return "\n".join(lines)


def _build_session_context(user: User, trigger: str) -> str:
    """Build session context based on trigger."""
    name = user.nickname or user.preferred_name
    triggers = {
        "user_initiated": f"{name} started a conversation.",
        "morning_checkin": (
            f"This is the morning check-in for {name}. "
            "Summarize what needs attention today."
        ),
        "document_arrived": (
            f"A new document was just processed for {name}. "
            "IMPORTANT: You MUST call get_pending_reviews first "
            "before saying anything about documents. Do NOT guess "
            "or fabricate document details. Only present facts "
            "returned by the tool."
        ),
        "document_review": (
            f"{name} wants to review a pending document. "
            "IMPORTANT: You MUST call get_pending_reviews first "
            "before saying anything about documents. Do NOT guess "
            "or fabricate document details. Only present facts "
            "returned by the tool. Present one document at a time."
        ),
        "notification_tapped": (
            f"{name} tapped a notification. "
            "Address the specific item they tapped."
        ),
    }
    return triggers.get(trigger, f"{name} is interacting with {BRAND_MID}.")


async def _build_document_context(
    db: AsyncSession, user_id: UUID, query: str
) -> str:
    """Retrieve relevant document chunks via RAG."""
    try:
        from app.conversation.retrieval import (
            retrieve_relevant_chunks,
        )
        chunks = await retrieve_relevant_chunks(
            db, user_id, query
        )
        if not chunks:
            return ""
        lines = [
            "Relevant information from the user's documents:"
        ]
        for c in chunks:
            source = c["source_field"].replace("_", " ")
            doc_type = c.get("classification", "document")
            lines.append(
                f"- [{doc_type}/{source}] {c['chunk_text']}"
            )
        return "\n".join(lines)
    except Exception:
        logger.warning(
            "RAG retrieval failed for user %s", user_id,
            exc_info=True,
        )
        return ""


async def _build_alerts_context(db: AsyncSession, user_id: UUID) -> str:
    """Build context from urgent items across sections."""
    from datetime import date, timedelta

    lines = []
    today = date.today()
    soon = today + timedelta(days=2)

    # Upcoming bills
    result = await db.execute(
        select(Bill).where(
            Bill.user_id == user_id,
            Bill.due_date <= soon,
            Bill.payment_status.in_(["pending", "acknowledged"]),
        )
    )
    bills = result.scalars().all()
    for b in bills:
        lines.append(
            f"- Bill: {b.sender} ${b.amount} due {b.due_date}"
        )

    # Upcoming appointments
    from datetime import datetime
    tomorrow = datetime.combine(
        today + timedelta(days=2), datetime.min.time()
    )
    result = await db.execute(
        select(Appointment).where(
            Appointment.user_id == user_id,
            Appointment.appointment_at <= tomorrow,
        )
    )
    appts = result.scalars().all()
    for a in appts:
        lines.append(
            f"- Appointment: {a.provider_name} on {a.appointment_at}"
        )

    # Pending document reviews
    try:
        from app.models.enums import ReviewStatus
        from app.models.pending_review import PendingReview
        async with db.begin_nested():
            result = await db.execute(
                select(PendingReview).where(
                    PendingReview.user_id == user_id,
                    PendingReview.review_status.in_(
                        [ReviewStatus.PENDING, ReviewStatus.PRESENTED]
                    ),
                ).order_by(
                    PendingReview.is_urgent.desc(),
                    PendingReview.created_at.desc(),
                )
            )
            review = result.scalar_one_or_none()
    except Exception:
        logger.warning(
            "Failed to query pending reviews for user %s",
            user_id, exc_info=True,
        )
        review = None
    if review:
        data = review.proposed_record_data or {}
        sender = data.get("sender", "someone")
        amount = data.get("amount_due", "")
        desc = f"from {review.source_description}"
        if review.recommended_action == "add_bill" and amount:
            lines.append(
                f"- Pending review: Bill {desc} — "
                f"{sender}, ${amount}"
            )
        else:
            lines.append(
                f"- Pending review: Document {desc} — "
                f"{review.recommended_action}"
            )
        if review.is_past_due:
            lines.append("  (This bill is past due)")
        if review.is_duplicate:
            lines.append("  (Possible duplicate)")

    if not lines:
        return ""
    return "Items needing attention:\n" + "\n".join(lines)
