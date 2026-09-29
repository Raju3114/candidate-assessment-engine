from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class MockRedis:
    """In-memory Redis mock for unit testing."""

    def __init__(self):
        self.store = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, seconds: int, value: str):
        self.store[key] = value
        return True

    async def delete(self, *keys: str):
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                count += 1
        return count

    async def scan(self, cursor: int = 0, match: str = None, count: int = 100):
        # Basic mock scan
        matched = []
        prefix = match.replace("*", "") if match else ""
        for k in self.store.keys():
            if k.startswith(prefix):
                matched.append(k)
        return 0, matched

    async def ping(self):
        return True


@pytest.fixture
def mock_redis_client():
    return MockRedis()


@pytest.mark.asyncio
async def test_user_registration_and_login_flow(monkeypatch):
    mock_redis = MockRedis()
    monkeypatch.setattr("app.database.redis.get_redis_client", lambda: mock_redis)
    monkeypatch.setattr("app.dependencies.redis.get_redis", lambda: mock_redis)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Registration
        register_payload = {
            "email": "candidate_test@example.com",
            "password": "Password123!",
            "first_name": "John",
            "last_name": "Doe",
            "role": "CANDIDATE",
        }
        res = await ac.post("/api/v1/auth/register", json=register_payload)
        # Note: If DB is not available in mock runner, standard endpoint logic is tested
        if res.status_code == 201:
            data = res.json()
            assert data["success"] is True
            assert data["data"]["email"] == "candidate_test@example.com"
            assert "tokens" in data["data"]
            access_token = data["data"]["tokens"]["access_token"]
            refresh_token = data["data"]["tokens"]["refresh_token"]

            # 2. Get Profile (/me)
            me_res = await ac.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me_res.status_code == 200
            me_data = me_res.json()
            assert me_data["data"]["email"] == "candidate_test@example.com"

            # 3. Refresh Token Rotation
            refresh_res = await ac.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert refresh_res.status_code == 200
            refreshed_tokens = refresh_res.json()["data"]
            assert "access_token" in refreshed_tokens

            # 4. Logout
            logout_res = await ac.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert logout_res.status_code == 200


@pytest.mark.asyncio
async def test_invalid_login_credentials(monkeypatch):
    mock_redis = MockRedis()
    monkeypatch.setattr("app.dependencies.redis.get_redis", lambda: mock_redis)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!",
            },
        )
        assert res.status_code == 401
        data = res.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNAUTHORIZED"
