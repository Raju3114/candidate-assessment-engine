import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_liveness_health_probe():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_request_id_header_middleware():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/health")
        assert "X-Request-ID" in res.headers
        assert "X-Process-Time" in res.headers


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/metrics")
        assert res.status_code == 200
        assert "http_requests_total" in res.text
        assert "active_websocket_connections" in res.text
