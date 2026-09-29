import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import logger
from app.core.metrics import metrics_registry


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware attaching correlation IDs (X-Request-ID), measuring latency,
    logging structured JSON metrics, and recording Prometheus counters.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()
        endpoint = request.url.path
        method = request.method

        # Skip logging for health & readiness probes
        is_probe = endpoint in ["/health", "/ready", "/api/v1/health", "/metrics"]

        if not is_probe:
            logger.info(
                f"Incoming HTTP {method} {endpoint}",
                extra={
                    "request_id": request_id,
                    "endpoint": endpoint,
                    "method": method,
                },
            )

        try:
            response = await call_next(request)
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time_ms}ms"

            # Record Prometheus metrics
            metrics_registry.inc_request(method, endpoint, response.status_code)

            if not is_probe:
                logger.info(
                    f"Outgoing HTTP {method} {endpoint} - Status {response.status_code} ({process_time_ms}ms)",
                    extra={
                        "request_id": request_id,
                        "endpoint": endpoint,
                        "method": method,
                        "status_code": response.status_code,
                        "latency_ms": process_time_ms,
                    },
                )

            return response

        except Exception as exc:
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled Exception on HTTP {method} {endpoint}: {str(exc)}",
                extra={
                    "request_id": request_id,
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": 500,
                    "latency_ms": process_time_ms,
                },
                exc_info=True,
            )
            raise exc
