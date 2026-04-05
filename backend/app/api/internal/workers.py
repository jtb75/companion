"""Internal API — Worker endpoints for Cloud Scheduler.

Authenticated via X-Pipeline-Key header (same as Pub/Sub push).
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)


async def verify_pipeline_key(
    x_pipeline_key: str | None = Header(
        None, alias="X-Pipeline-Key"
    ),
):
    """Verify pipeline API key for service-to-service auth."""
    if not settings.pipeline_api_key:
        if settings.environment in ("development", "test"):
            return
        raise HTTPException(
            503, "Pipeline API key not configured"
        )
    if x_pipeline_key != settings.pipeline_api_key:
        raise HTTPException(401, "Invalid pipeline API key")


router = APIRouter(
    prefix="/api/internal/workers",
    tags=["Internal - Workers"],
    dependencies=[Depends(verify_pipeline_key)],
)


@router.post("/morning-checkin")
async def morning_checkin():
    """Called by Cloud Scheduler every minute."""
    from app.workers.morning_trigger import run_morning_trigger

    result = await run_morning_trigger()
    return result


@router.post("/medication-reminders")
async def medication_reminders():
    """Called by Cloud Scheduler every minute."""
    from app.workers.medication_reminder import (
        run_medication_reminder,
    )

    result = await run_medication_reminder()
    return result
