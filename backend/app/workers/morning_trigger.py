"""Morning check-in trigger — fires check-in for each user at their configured time.

In production, Cloud Scheduler calls this endpoint every minute.
The worker checks which users have a check-in due and fires events.
"""

import logging
from datetime import datetime, time

from sqlalchemy import select

from app.db.session import async_session_factory
from app.events.publisher import event_publisher
from app.events.schemas import CheckinMorningTriggeredPayload
from app.models.user import User
from app.notifications.briefing import generate_morning_briefing
from app.notifications.morning_checkin import assemble_morning_checkin

logger = logging.getLogger(__name__)


async def run_morning_trigger(force: bool = False):
    """Check all users and trigger morning check-ins where due."""
    async with async_session_factory() as db:
        try:
            now = datetime.utcnow()
            current_hour = now.hour
            current_minute = now.minute

            # Find active users
            result = await db.execute(
                select(User).where(User.account_status == "active")
            )
            users = result.scalars().all()

            triggered = 0
            for user in users:
                checkin_time = user.checkin_time or time(9, 0)

                # Skip if not the right time (unless forced)
                if not force:
                    if checkin_time.hour != current_hour:
                        continue
                    if abs(checkin_time.minute - current_minute) > 5:
                        continue

                # Skip if in away mode
                if user.away_mode:
                    continue

                # Assemble check-in data
                name = user.nickname or user.preferred_name
                checkin_data = await assemble_morning_checkin(
                    db, user.id, name
                )
                
                # Generate LLM briefing
                briefing = await generate_morning_briefing(
                    db, user.id, checkin_data
                )

                await event_publisher.publish(
                    "checkin.morning.triggered",
                    user_id=user.id,
                    payload=CheckinMorningTriggeredPayload(
                        user_id=user.id,
                        checkin_time=str(checkin_time),
                        items_count=checkin_data.get("total_items", 0),
                        briefing=briefing,
                    ),
                )
                triggered += 1

            await db.commit()
            logger.info(
                f"Morning trigger: {triggered}/{len(users)} "
                f"check-ins fired at {current_hour}:{current_minute:02d}"
            )
            return {
                "total_users": len(users),
                "triggered": triggered,
            }
        except Exception:
            await db.rollback()
            logger.exception("Morning trigger failed")
            raise
