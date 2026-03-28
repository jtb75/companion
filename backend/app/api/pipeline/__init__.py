"""Pipeline API — aggregates pipeline internal routers."""

from fastapi import APIRouter

from app.api.pipeline import results

router = APIRouter()

router.include_router(results.router)
