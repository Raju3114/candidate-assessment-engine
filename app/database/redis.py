import logging
from typing import Optional

from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

redis_client: Optional[Redis] = None


async def init_redis() -> Redis:
    """Initializes the global Redis connection pool."""
    global redis_client
    if redis_client is None:
        logger.info("Initializing Redis connection pool...")
        redis_client = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await redis_client.ping()
        logger.info("Redis connected successfully.")
    return redis_client


async def close_redis() -> None:
    """Closes the global Redis connection pool."""
    global redis_client
    if redis_client is not None:
        logger.info("Closing Redis connection pool...")
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed.")


def get_redis_client() -> Redis:
    """Returns the initialized Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized. Call init_redis() first.")
    return redis_client
