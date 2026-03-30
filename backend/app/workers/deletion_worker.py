"""Deletion worker — executes pending account deletions past their grace period.

Runs nightly. Each user deletion commits independently so failures don't block others.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import async_session_factory
from app.integrations.email_service import send_account_deleted_to_caregiver
from app.models.user import User
from app.services.account_lifecycle_service import execute_deletion

logger = logging.getLogger(__name__)


async def run_deletion_worker():
    """Execute pending account deletions past their grace period."""
    async with async_session_factory() as db:
        try:
            now = datetime.now(UTC)
            result = await db.execute(
                select(User).where(
                    User.account_status == "pending_deletion",
                    User.deletion_scheduled_at <= now,
                )
            )
            users = result.scalars().all()

            deleted_count = 0
            for user in users:
                try:
                    name = user.preferred_name or user.display_name
                    deletion_result = await execute_deletion(db, user.id)
                    await db.commit()

                    # Notify caregivers after successful deletion
                    for email, cname in deletion_result.get("caregivers", []):
                        await send_account_deleted_to_caregiver(email, cname, name)

                    deleted_count += 1
                    logger.info(f"Deleted user {user.id} ({user.email})")
                except Exception:
                    await db.rollback()
                    logger.exception(f"Failed to delete user {user.id}")

            logger.info(
                f"Deletion worker complete: "
                f"{len(users)} pending, {deleted_count} deleted"
            )
            return {"pending": len(users), "deleted": deleted_count}
        except Exception:
            logger.exception("Deletion worker failed")
            raise
