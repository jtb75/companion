"""Internal API — endpoints called by Cloud Scheduler."""

from fastapi import APIRouter

from app.api.internal import workers

router = APIRouter()
router.include_router(workers.router)
