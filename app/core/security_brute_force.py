import logging
from redis.asyncio import Redis

from app.core.exceptions import ForbiddenException

logger = logging.getLogger("app.security")


class BruteForceProtector:
    """Tracks failed authentication attempts in Redis and enforces exponential lockout penalties."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def check_lockout(self, ip_address: str, email: str) -> None:
        """Verifies if the IP or email account is currently under lockout."""
        lockout_key = f"lockout:{ip_address}:{email.lower()}"
        is_locked = await self.redis.get(lockout_key)
        if is_locked:
            ttl = await self.redis.ttl(lockout_key)
            logger.warning(f"Security Alert: Blocked brute force attempt on locked account '{email}' from IP '{ip_address}' (TTL: {ttl}s)")
            raise ForbiddenException(
                message=f"Account temporarily locked due to repeated failed login attempts. Try again in {max(1, ttl // 60)} minutes.",
                details={"lockout_seconds": ttl},
            )

    async def record_failed_attempt(self, ip_address: str, email: str) -> int:
        """Increments failed attempt counter and applies lockout if threshold exceeded."""
        key = f"failed_logins:{ip_address}:{email.lower()}"
        attempts = await self.redis.incr(key)
        await self.redis.expire(key, 86400)  # Keep window for 24 hours

        lockout_seconds = 0
        if attempts >= 15:
            lockout_seconds = 86400  # 24 Hours
        elif attempts >= 10:
            lockout_seconds = 1800  # 30 Minutes
        elif attempts >= 5:
            lockout_seconds = 300  # 5 Minutes

        if lockout_seconds > 0:
            lockout_key = f"lockout:{ip_address}:{email.lower()}"
            await self.redis.setex(lockout_key, lockout_seconds, "locked")
            logger.warning(f"Security Action: Applied {lockout_seconds}s lockout for '{email}' from IP '{ip_address}' (Failed attempts: {attempts})")

        return attempts

    async def reset_failed_attempts(self, ip_address: str, email: str) -> None:
        """Resets failed attempt counters on successful login."""
        key = f"failed_logins:{ip_address}:{email.lower()}"
        lockout_key = f"lockout:{ip_address}:{email.lower()}"
        await self.redis.delete(key, lockout_key)
