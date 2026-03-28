"""Admin API — Pipeline health monitoring."""

import uuid

from fastapi import APIRouter, Depends

from app.auth.dependencies import AdminUser, require_admin_role

router = APIRouter(prefix="/admin/pipeline", tags=["Admin - Pipeline Health"])

_viewer = require_admin_role("viewer")


@router.get("/health")
async def pipeline_health(admin: AdminUser = Depends(_viewer)):
    """Overall pipeline health status."""
    # TODO: aggregate pipeline health metrics
    return {
        "status": "healthy",
        "stages": {
            "classification": {"status": "ok", "avg_latency_ms": 0},
            "extraction": {"status": "ok", "avg_latency_ms": 0},
            "summary": {"status": "ok", "avg_latency_ms": 0},
            "routing": {"status": "ok", "avg_latency_ms": 0},
        },
        "queue_depth": 0,
    }


@router.get("/metrics")
async def pipeline_metrics(admin: AdminUser = Depends(_viewer)):
    """Pipeline processing metrics."""
    # TODO: query pipeline metrics
    return {
        "documents_processed_24h": 0,
        "avg_processing_time_ms": 0,
        "success_rate": 1.0,
        "by_stage": {},
    }


@router.get("/failures")
async def pipeline_failures(admin: AdminUser = Depends(_viewer)):
    """Recent pipeline failures."""
    # TODO: query recent pipeline failures
    return {
        "failures": [],
        "total": 0,
    }


@router.get("/documents/{document_id}/stages")
async def document_stages(
    document_id: uuid.UUID, admin: AdminUser = Depends(_viewer)
):
    """Pipeline stage details for a specific document."""
    # TODO: query pipeline stages for this document
    return {
        "document_id": str(document_id),
        "stages": [],
    }
