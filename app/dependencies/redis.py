from redis.asyncio import Redis
from app.database.redis import get_redis_client


def get_redis() -> Redis:
    """Dependency injection provider for Redis client."""
    return get_redis_client()
