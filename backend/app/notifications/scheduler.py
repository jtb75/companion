from __future__ import annotations

import logging
from datetime import datetime, time

from app.models.user import User

logger = logging.getLogger(__name__)


def is_quiet_hours(user: User) -> bool:
    """Check if current time is within user's quiet hours."""
    now = datetime.utcnow().time()
    start = user.quiet_start or time(21, 0)
    end = user.quiet_end or time(8, 0)

    if start < end:
        # Normal range (e.g., 21:00 - 23:00)
        return start <= now <= end
    else:
        # Wraps midnight (e.g., 21:00 - 08:00)
        return now >= start or now <= end


def should_deliver(
    priority_level: int, user: User, attempt: int = 1
) -> dict:
    """Decide whether and how to deliver a notification.

    Returns a dict with:
      deliver: bool
      channel: str (voice, push, in_app, morning_checkin)
      reason: str
    """
    quiet = is_quiet_hours(user)

    # Level 1 (Urgent) — always deliver, break quiet hours
    if priority_level == 1:
        return {
            "deliver": True,
            "channel": "push",
            "reason": "urgent_breaks_quiet" if quiet else "urgent",
            "prefix": (
                "Sorry to bother you late — this is important. "
                if quiet else ""
            ),
        }

    # During quiet hours, queue everything except Level 1
    if quiet:
        return {
            "deliver": False,
            "channel": "morning_checkin",
            "reason": "quiet_hours",
        }

    # Diminishing repetition
    if attempt >= 3:
        return {
            "deliver": False,
            "channel": "morning_checkin",
            "reason": "max_attempts_reached",
        }

    if attempt == 2 and priority_level > 2:
        return {
            "deliver": False,
            "channel": "morning_checkin",
            "reason": "low_priority_second_attempt",
        }

    # Normal delivery
    channel = "push"  # default
    return {
        "deliver": True,
        "channel": channel,
        "reason": "normal",
    }
