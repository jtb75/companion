"""Pipeline API — Internal service endpoints for document processing results.

These endpoints are called by the pipeline workers to post processing results.
Authenticated via X-Pipeline-Key header (service-to-service auth).
"""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import settings


async def verify_pipeline_key(
    x_pipeline_key: str | None = Header(None, alias="X-Pipeline-Key"),
):
    """Verify pipeline API key for service-to-service auth."""
    # Allow in dev/test if no key configured
    if not settings.pipeline_api_key:
        if settings.environment in ("development", "test"):
            return
        raise HTTPException(503, "Pipeline API key not configured")

    if x_pipeline_key != settings.pipeline_api_key:
        raise HTTPException(401, "Invalid pipeline API key")


router = APIRouter(tags=["Pipeline"], dependencies=[Depends(verify_pipeline_key)])


@router.post(
    "/pipeline/documents/{document_id}/classification",
    status_code=status.HTTP_201_CREATED,
)
async def post_classification(document_id: uuid.UUID):
    """Receive classification result from pipeline."""
    # TODO: accept classification payload and update document
    return {
        "document_id": str(document_id),
        "stage": "classification",
        "accepted": True,
    }


@router.post(
    "/pipeline/documents/{document_id}/extraction",
    status_code=status.HTTP_201_CREATED,
)
async def post_extraction(document_id: uuid.UUID):
    """Receive extraction result from pipeline."""
    # TODO: accept extraction payload and update document
    return {
        "document_id": str(document_id),
        "stage": "extraction",
        "accepted": True,
    }


@router.post(
    "/pipeline/documents/{document_id}/summary",
    status_code=status.HTTP_201_CREATED,
)
async def post_summary(document_id: uuid.UUID):
    """Receive summary result from pipeline."""
    # TODO: accept summary payload and update document
    return {
        "document_id": str(document_id),
        "stage": "summary",
        "accepted": True,
    }


@router.post(
    "/pipeline/documents/{document_id}/route",
    status_code=status.HTTP_201_CREATED,
)
async def post_route(document_id: uuid.UUID):
    """Receive routing result from pipeline."""
    # TODO: accept routing payload and update document
    return {
        "document_id": str(document_id),
        "stage": "route",
        "accepted": True,
    }


@router.post(
    "/pipeline/documents/{document_id}/status",
    status_code=status.HTTP_201_CREATED,
)
async def post_status(document_id: uuid.UUID):
    """Receive status update from pipeline."""
    # TODO: accept status payload and update document
    return {
        "document_id": str(document_id),
        "stage": "status",
        "accepted": True,
    }


@router.post("/pipeline/questions", status_code=status.HTTP_201_CREATED)
async def post_questions():
    """Receive generated questions from pipeline."""
    # TODO: accept questions payload and persist for Arlo
    return {
        "accepted": True,
        "questions_count": 0,
    }
