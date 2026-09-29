from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints.health import liveness_probe, metrics_endpoint, readiness_probe
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exception_handlers import (
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import BaseAppException
from app.core.logging import setup_logging
from app.core.telemetry import setup_opentelemetry
from app.database.redis import close_redis, init_redis
from app.database.session import engine
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.observability import ObservabilityMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.websocket.routes import router as websocket_router

# Setup Structured JSON Logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI Lifespan Manager handling application startup and shutdown events.
    Initializes and tears down persistent connections (DB Engine, Redis Pool).
    """
    logger.info(f"Starting {settings.PROJECT_NAME} [{settings.ENVIRONMENT}]...")
    
    # 1. Initialize Redis Pool
    try:
        await init_redis()
    except Exception as exc:
        logger.error(f"Failed to connect to Redis on startup: {exc}")

    # 2. Verify Database Pool Connectivity
    try:
        async with engine.begin() as conn:
            logger.info("PostgreSQL database connection pool verified.")
    except Exception as exc:
        logger.error(f"Failed to verify PostgreSQL connection on startup: {exc}")

    yield

    # Shutdown Phase
    logger.info("Shutting down application server...")
    
    # 1. Close Redis Pool
    await close_redis()

    # 2. Dispose Database Engine
    logger.info("Disposing PostgreSQL database engine pool...")
    await engine.dispose()
    logger.info("Shutdown sequence completed.")


def create_application() -> FastAPI:
    """Application factory initializing FastAPI with middleware, routers, and handlers."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 1. Security Response Headers Middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. Rate Limiting Middleware
    app.add_middleware(RateLimitMiddleware)

    # 3. Idempotency Key Protection Middleware
    app.add_middleware(IdempotencyMiddleware)

    # 4. Observability Correlation ID Middleware
    app.add_middleware(ObservabilityMiddleware)

    # 5. Environment-Driven CORS Middleware Setup
    if settings.ALLOWED_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    # 6. Global Exception Handler Registrations
    app.add_exception_handler(BaseAppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 7. Root Health, Readiness & Metrics Endpoints
    app.add_api_route("/health", liveness_probe, methods=["GET"], tags=["Observability"])
    app.add_api_route("/ready", readiness_probe, methods=["GET"], tags=["Observability"])
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], tags=["Observability"])

    # 8. Router Registrations
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)
    app.include_router(websocket_router)

    # 9. OpenTelemetry Tracing Setup Hook
    setup_opentelemetry(app)

    return app


app = create_application()
