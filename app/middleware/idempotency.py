import json
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse

from app.database.redis import get_redis_client

logger = logging.getLogger("app.security")


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware preventing duplicate execution of POST operations via 'X-Idempotency-Key' headers.
    Caches successful responses in Redis for 1 hour.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        idempotency_key = request.headers.get("X-Idempotency-Key")

        # Only apply to POST requests supplying an X-Idempotency-Key header
        if request.method != "POST" or not idempotency_key:
            return await call_next(request)

        try:
            redis = get_redis_client()
            cache_key = f"idempotency:{idempotency_key}"

            # 1. Check if response is cached
            cached_data = await redis.get(cache_key)
            if cached_data:
                logger.info(f"Idempotency HIT for key '{idempotency_key}' - Returning cached execution result.")
                parsed = json.loads(cached_data)
                return Response(
                    content=parsed["body"],
                    status_code=parsed["status_code"],
                    media_type=parsed.get("media_type", "application/json"),
                    headers={"X-Cache": "IDEMPOTENCY-HIT"},
                )

            # 2. Execute Request
            response = await call_next(request)

            # Cache successful 2xx responses
            if 200 <= response.status_code < 300:
                response_body = [section async for section in response.body_iterator]
                response.body_iterator = iterate_in_chunks(response_body)
                body_bytes = b"".join(response_body)

                payload_to_cache = {
                    "status_code": response.status_code,
                    "body": body_bytes.decode("utf-8", errors="ignore"),
                    "media_type": response.media_type,
                }

                # Store in Redis with TTL 1 hour (3600s)
                await redis.setex(cache_key, 3600, json.dumps(payload_to_cache))

            return response

        except Exception as exc:
            logger.error(f"Idempotency middleware error: {exc}")
            return await call_next(request)


async def iterate_in_chunks(chunks):
    for chunk in chunks:
        yield chunk
