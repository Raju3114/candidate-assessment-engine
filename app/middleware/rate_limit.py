import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.exceptions import BaseAppException
from app.core.logging import logger
from app.database.redis import get_redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter enforcing endpoint, auth, and global quotas."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        endpoint = request.url.path
        method = request.method
        ip_address = request.client.host if request.client else "127.0.0.1"

        # Skip health checks
        if endpoint in ["/health", "/ready", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)

        try:
            redis = get_redis_client()
            now = int(time.time())

            # 1. Auth Endpoint Limits (5 requests / 60 seconds / IP)
            if endpoint.endswith("/auth/login") and method == "POST":
                key = f"ratelimit:auth:{ip_address}"
                req_count = await redis.incr(key)
                if req_count == 1:
                    await redis.expire(key, 60)
                if req_count > 5:
                    logger.warning(f"Rate limit exceeded on Auth endpoint for IP '{ip_address}'")
                    return Response(
                        content='{"success": false, "data": null, "error": {"code": "TOO_MANY_REQUESTS", "message": "Login rate limit exceeded. Please wait 1 minute.", "details": null}}',
                        status_code=429,
                        media_type="application/json",
                    )

            # 2. AI Heavy Endpoints Limits (20 requests / 3600 seconds / IP)
            elif "generate" in endpoint or "evaluate" in endpoint:
                key = f"ratelimit:ai:{ip_address}"
                req_count = await redis.incr(key)
                if req_count == 1:
                    await redis.expire(key, 3600)
                if req_count > 20:
                    logger.warning(f"Rate limit exceeded on AI endpoint for IP '{ip_address}'")
                    return Response(
                        content='{"success": false, "data": null, "error": {"code": "TOO_MANY_REQUESTS", "message": "AI generation rate limit exceeded (20 req/hour).", "details": null}}',
                        status_code=429,
                        media_type="application/json",
                    )

            # 3. Global Endpoint Limits (100 requests / 60 seconds / IP)
            else:
                key = f"ratelimit:global:{ip_address}"
                req_count = await redis.incr(key)
                if req_count == 1:
                    await redis.expire(key, 60)
                if req_count > 100:
                    logger.warning(f"Global rate limit exceeded for IP '{ip_address}'")
                    return Response(
                        content='{"success": false, "data": null, "error": {"code": "TOO_MANY_REQUESTS", "message": "Global rate limit exceeded (100 req/min).", "details": null}}',
                        status_code=429,
                        media_type="application/json",
                    )

        except Exception as exc:
            # Fall through gracefully if Redis temporary check fails
            logger.error(f"Rate limiter Redis check error: {exc}")

        return await call_next(request)
