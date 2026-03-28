from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass
class NotificationItem:
    """An item that may need to be notified about."""
    id: UUID
    user_id: UUID
    item_type: str  # bill, medication, appointment, document, todo
    title: str
    detail: str = ""
    priority_level: int = 4  # 1=urgent, 2=act_today, 3=needs_attention, 4=routine
    relevant_date: date | None = None
    category: str = ""  # for documents: legal, junk, etc.
    escalated: bool = False
    acknowledged: bool = False


def assign_priority(item: NotificationItem) -> int:
    """Assign priority level 1-4 based on item type and timing."""
    today = date.today()

    # Legal/eviction/collections always urgent
    if item.category in ("legal", "eviction", "collections"):
        return 1

    # Escalated items promote to level 1
    if item.escalated:
        return 1

    # Bills
    if item.item_type == "bill" and item.relevant_date:
        days_until = (item.relevant_date - today).days
        if days_until < 0:  # overdue
            return 1
        if days_until < 2:  # due within 48 hours
            return 2
        if days_until < 7:
            return 3
        return 4

    # Appointments
    if item.item_type == "appointment" and item.relevant_date:
        days_until = (item.relevant_date - today).days
        if days_until <= 0:  # today
            return 2
        if days_until <= 1:  # tomorrow
            return 2
        if days_until < 7:
            return 3
        return 4

    # Medication missed today
    if item.item_type == "medication" and item.category == "missed":
        return 2

    # Medication refill
    if item.item_type == "medication" and item.category == "refill":
        return 3

    # Documents
    if item.item_type == "document":
        urgency_map = {
            "urgent": 1,
            "act_today": 2,
            "needs_attention": 3,
            "routine": 4,
        }
        return urgency_map.get(item.category, 4)

    return 4


def priority_label(level: int) -> str:
    """User-facing urgency label."""
    return {1: "Today", 2: "Today", 3: "Soon", 4: "Can Wait"}.get(level, "Can Wait")


PRIORITY_LABELS = {
    1: "Urgent",
    2: "Act Today",
    3: "Needs Attention",
    4: "Routine",
}
