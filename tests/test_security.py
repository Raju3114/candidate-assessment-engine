import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security_brute_force import BruteForceProtector
from app.main import app


@pytest.mark.asyncio
async def test_security_headers_middleware():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'self'" in res.headers["Content-Security-Policy"]
        assert "max-age=31536000" in res.headers["Strict-Transport-Security"]


class MockRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def incr(self, key: str):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, seconds: int):
        self.ttls[key] = seconds
        return True

    async def ttl(self, key: str):
        return self.ttls.get(key, 300)

    async def setex(self, key: str, seconds: int, value: str):
        self.store[key] = value
        self.ttls[key] = seconds
        return True

    async def delete(self, *keys: str):
        for k in keys:
            self.store.pop(k, None)
            self.ttls.pop(k, None)
        return True


@pytest.mark.asyncio
async def test_brute_force_lockout_escalation():
    redis_mock = MockRedis()
    protector = BruteForceProtector(redis_mock)

    ip = "192.168.1.100"
    email = "attacker@example.com"

    # Simulate 5 failed attempts
    for _ in range(5):
        attempts = await protector.record_failed_attempt(ip, email)

    assert attempts == 5
    # Should now have lockout key set
    assert await redis_mock.get(f"lockout:{ip}:{email.lower()}") == "locked"
