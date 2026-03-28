from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.publisher import event_publisher
from app.events.schemas import (
    CaregiverAlertTriggeredPayload,
    QuestionThresholdCrossedPayload,
)
from app.models.enums import QuestionStatus
from app.models.question_tracker import QuestionTracker
from app.models.trusted_contact import TrustedContact

logger = logging.getLogger(__name__)


async def check_escalations(db: AsyncSession, user_id: UUID) -> list[dict]:
    """Check all open questions for escalation threshold crossings.

    Returns list of escalated items.
    """
    now = datetime.utcnow()

    result = await db.execute(
        select(QuestionTracker).where(
            QuestionTracker.user_id == user_id,
            QuestionTracker.status == QuestionStatus.OPEN,
        )
    )
    questions = result.scalars().all()

    escalated = []

    for q in questions:
        hours_open = (now - q.asked_at).total_seconds() / 3600
        threshold = q.escalation_threshold_hours or 24

        if hours_open >= threshold and q.escalated_at is None:
            # Mark as escalated
            q.status = QuestionStatus.ESCALATED
            q.escalated_at = now

            # Find trusted contacts for alerts
            contacts_result = await db.execute(
                select(TrustedContact).where(
                    TrustedContact.user_id == user_id,
                    TrustedContact.is_active.is_(True),
                )
            )
            contacts = contacts_result.scalars().all()
            contact_ids = [c.id for c in contacts]

            # Emit events
            await event_publisher.publish(
                "question.threshold_crossed",
                user_id=user_id,
                payload=QuestionThresholdCrossedPayload(
                    question_id=q.id,
                    hours_open=hours_open,
                    escalation_threshold_hours=threshold,
                    trusted_contact_ids=contact_ids,
                ),
            )

            # Trigger caregiver alerts
            for contact in contacts:
                await event_publisher.publish(
                    "caregiver.alert.triggered",
                    user_id=user_id,
                    payload=CaregiverAlertTriggeredPayload(
                        trusted_contact_id=contact.id,
                        alert_type="question_escalation",
                        context={
                            "question": q.question_text[:100],
                            "hours_open": round(hours_open, 1),
                            "context_type": (
                                q.context_type.value
                                if hasattr(q.context_type, "value")
                                else str(q.context_type)
                            ),
                        },
                    ),
                )

            escalated.append({
                "question_id": str(q.id),
                "question_text": q.question_text,
                "hours_open": round(hours_open, 1),
                "threshold": threshold,
                "contacts_notified": len(contacts),
            })

            logger.info(
                f"Escalated question {q.id}: "
                f"{hours_open:.1f}h open "
                f"(threshold: {threshold}h)"
            )

    if escalated:
        await db.flush()

    return escalated


async def get_open_escalations(
    db: AsyncSession, user_id: UUID | None = None
) -> list[dict]:
    """Get all open questions approaching or past threshold."""
    now = datetime.utcnow()

    query = select(QuestionTracker).where(
        QuestionTracker.status.in_([
            QuestionStatus.OPEN,
            QuestionStatus.ESCALATED,
        ]),
    )
    if user_id:
        query = query.where(QuestionTracker.user_id == user_id)

    result = await db.execute(query.order_by(QuestionTracker.asked_at))
    questions = result.scalars().all()

    items = []
    for q in questions:
        hours_open = (now - q.asked_at).total_seconds() / 3600
        threshold = q.escalation_threshold_hours or 24
        items.append({
            "id": str(q.id),
            "user_id": str(q.user_id),
            "question_text": q.question_text,
            "context_type": (
                q.context_type.value
                if hasattr(q.context_type, "value")
                else str(q.context_type)
            ),
            "urgency_level": (
                q.urgency_level.value
                if hasattr(q.urgency_level, "value")
                else str(q.urgency_level)
            ),
            "hours_open": round(hours_open, 1),
            "threshold_hours": threshold,
            "pct_to_threshold": round(
                (hours_open / threshold) * 100, 1
            ) if threshold else 0,
            "status": (
                q.status.value
                if hasattr(q.status, "value")
                else str(q.status)
            ),
            "asked_at": q.asked_at.isoformat(),
            "escalated_at": (
                q.escalated_at.isoformat() if q.escalated_at else None
            ),
        })

    return items
