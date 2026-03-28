"""Basic health check test — async to avoid event loop conflicts."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="module")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac


async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
