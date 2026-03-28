"""Escalation check worker — monitors question tracker thresholds.

Runs every 15 minutes. Checks all open questions against their
escalation thresholds and triggers caregiver alerts when crossed.
"""

import logging

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.user import User
from app.notifications.escalation import check_escalations

logger = logging.getLogger(__name__)


async def run_escalation_check():
    """Check all users for questions past escalation thresholds."""
    async with async_session_factory() as db:
        try:
            result = await db.execute(select(User.id))
            user_ids = [row[0] for row in result.all()]

            total_escalated = 0
            for user_id in user_ids:
                escalated = await check_escalations(db, user_id)
                total_escalated += len(escalated)

            await db.commit()

            logger.info(
                f"Escalation check complete: "
                f"{len(user_ids)} users checked, "
                f"{total_escalated} escalated"
            )
            return {
                "users_checked": len(user_ids),
                "total_escalated": total_escalated,
            }
        except Exception:
            await db.rollback()
            logger.exception("Escalation check failed")
            raise
