import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_application_startup_smoke_test():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Health Liveness Probe
        health_res = await ac.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"

        # 2. OpenAPI Specification Accessibility
        openapi_res = await ac.get("/api/v1/openapi.json")
        assert openapi_res.status_code == 200
        spec = openapi_res.json()
        assert "paths" in spec

        # 3. Metrics Exposition
        metrics_res = await ac.get("/metrics")
        assert metrics_res.status_code == 200
        assert "http_requests_total" in metrics_res.text
