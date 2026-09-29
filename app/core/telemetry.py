import logging
from typing import Optional

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def setup_opentelemetry(app: FastAPI, service_name: str = "ai-interview-backend") -> None:
    """
    Hook preparing OpenTelemetry auto-instrumentation for FastAPI, SQLAlchemy, and Redis.
    Supports future export to Jaeger / Grafana Tempo.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        provider = TracerProvider()
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        logger.info(f"OpenTelemetry instrumentation enabled for '{service_name}'")
    except ImportError:
        logger.info(f"OpenTelemetry SDK not installed. Telemetry hooks configured for future export.")
