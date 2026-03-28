"""Admin API — aggregates admin-facing routers."""

from fastapi import APIRouter

from app.api.admin import admin_users, config, escalations, metrics, pipeline_health

router = APIRouter()

router.include_router(config.router)
router.include_router(pipeline_health.router)
router.include_router(escalations.router)
router.include_router(metrics.router)
router.include_router(admin_users.router)
