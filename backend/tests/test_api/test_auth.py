"""Unit tests for API authentication behavior."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


@pytest.fixture
def client():
    """Provide an httpx AsyncClient wired to the FastAPI app."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_unauthenticated_request_rejected(client: AsyncClient):
    """Without dev_auth_bypass, an unauthenticated request should be rejected."""
    original = settings.dev_auth_bypass
    try:
        settings.dev_auth_bypass = False
        resp = await client.get("/api/v1/medications")
        # Should get 401 or 403 when no Authorization header is provided
        assert resp.status_code in (401, 403, 422)
    finally:
        settings.dev_auth_bypass = original


async def test_pipeline_key_auth_valid(client: AsyncClient):
    """A valid X-Pipeline-Key header should be accepted by pipeline endpoints."""
    original_key = settings.pipeline_api_key
    try:
        settings.pipeline_api_key = "test-pipeline-secret"

        # The pipeline endpoint expects a specific payload format, but
        # we're testing auth, so we send a minimal body. We expect a 400
        # (bad payload) rather than 401 (unauthorized) if the key is valid.
        resp = await client.post(
            "/api/pipeline/document-received",
            json={"test": "data"},
            headers={"X-Pipeline-Key": "test-pipeline-secret"},
        )
        # Should NOT be 401 — the key is valid
        assert resp.status_code != 401
    finally:
        settings.pipeline_api_key = original_key


async def test_pipeline_key_auth_invalid(client: AsyncClient):
    """An invalid X-Pipeline-Key should be rejected with 401."""
    original_key = settings.pipeline_api_key
    try:
        settings.pipeline_api_key = "test-pipeline-secret"

        resp = await client.post(
            "/api/pipeline/document-received",
            json={"test": "data"},
            headers={"X-Pipeline-Key": "wrong-key"},
        )
        assert resp.status_code == 401
    finally:
        settings.pipeline_api_key = original_key
