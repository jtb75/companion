"""Pipeline API — aggregates pipeline internal routers."""

from fastapi import APIRouter

from app.api.pipeline import document_handler, results

router = APIRouter()

router.include_router(results.router)
router.include_router(document_handler.router)
