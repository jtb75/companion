"""Away mode monitor — checks for users in extended away mode.

Triggers Tier 1 caregiver alerts when a user has been in away mode
for 7+ days without checking in.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.session import async_session_factory
from app.events.publisher import event_publisher
from app.events.schemas import CaregiverAlertTriggeredPayload
from app.models.trusted_contact import TrustedContact
from app.models.user import User

logger = logging.getLogger(__name__)

AWAY_ALERT_THRESHOLD_DAYS = 7


async def run_away_monitor():
    """Check for users in extended away mode."""
    async with async_session_factory() as db:
        try:
            now = datetime.utcnow()
            threshold = now - timedelta(days=AWAY_ALERT_THRESHOLD_DAYS)

            result = await db.execute(
                select(User).where(
                    User.away_mode.is_(True),
                    User.away_expires_at.isnot(None),
                    User.away_expires_at < threshold,
                )
            )
            users = result.scalars().all()

            alerts_sent = 0
            for user in users:
                contacts_result = await db.execute(
                    select(TrustedContact).where(
                        TrustedContact.user_id == user.id,
                        TrustedContact.is_active.is_(True),
                    )
                )
                contacts = contacts_result.scalars().all()

                for contact in contacts:
                    await event_publisher.publish(
                        "caregiver.alert.triggered",
                        user_id=user.id,
                        payload=CaregiverAlertTriggeredPayload(
                            trusted_contact_id=contact.id,
                            alert_type="extended_away_mode",
                            context={
                                "away_since": (
                                    user.away_expires_at.isoformat()
                                    if user.away_expires_at
                                    else "unknown"
                                ),
                                "days_away": (
                                    now - user.away_expires_at
                                ).days if user.away_expires_at else 0,
                            },
                        ),
                    )
                    alerts_sent += 1

            await db.commit()
            logger.info(
                f"Away monitor: {len(users)} users in extended away, "
                f"{alerts_sent} alerts sent"
            )
            return {
                "users_in_extended_away": len(users),
                "alerts_sent": alerts_sent,
            }
        except Exception:
            await db.rollback()
            logger.exception("Away monitor failed")
            raise
