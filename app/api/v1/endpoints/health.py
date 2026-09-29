from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.metrics import metrics_registry
from app.core.responses import ApiResponse
from app.dependencies.database import get_db
from app.dependencies.redis import get_redis
from app.schemas.common import HealthCheckResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    summary="Basic Liveness Probe",
    description="Returns simple 200 OK indicating the application process is running.",
)
async def liveness_probe() -> dict:
    return {"status": "healthy"}


@router.get(
    "/ready",
    summary="Readiness Probe",
    description="Probes connectivity to PostgreSQL, Redis, and Gemini API services.",
)
async def readiness_probe(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> dict:
    pg_status = "error"
    redis_status = "error"
    gemini_status = "configured" if settings.GEMINI_API_KEY else "unconfigured"

    # PostgreSQL Check
    try:
        res = await db.execute(text("SELECT 1"))
        if res.scalar() == 1:
            pg_status = "ok"
    except Exception as exc:
        logger.error(f"Readiness PG probe error: {exc}")

    # Redis Check
    try:
        if await redis.ping():
            redis_status = "ok"
    except Exception as exc:
        logger.error(f"Readiness Redis probe error: {exc}")

    is_ready = pg_status == "ok" and redis_status == "ok"
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        content=f'{{"postgres": "{pg_status}", "redis": "{redis_status}", "gemini": "{gemini_status}"}}',
        media_type="application/json",
        status_code=status_code,
    )


@router.get(
    "/metrics",
    summary="Prometheus Metrics Exposition",
    description="Exposes application counters and gauges in Prometheus text exposition format.",
)
async def metrics_endpoint() -> Response:
    content = metrics_registry.generate_prometheus_metrics()
    return Response(content=content, media_type="text/plain; version=0.0.4")
