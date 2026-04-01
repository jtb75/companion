"""Admin API — aggregates admin-facing routers."""

from fastapi import APIRouter

from app.api.admin import (
    admin_users,
    config,
    contacts,
    conversations,
    escalations,
    metrics,
    people,
    pipeline_health,
    test_email,
    users_management,
    workers,
)

router = APIRouter()

router.include_router(config.router)
router.include_router(conversations.router)
router.include_router(pipeline_health.router)
router.include_router(escalations.router)
router.include_router(metrics.router)
router.include_router(admin_users.router)
router.include_router(contacts.router)
router.include_router(users_management.router)
router.include_router(people.router)
router.include_router(test_email.router)
router.include_router(workers.router)
