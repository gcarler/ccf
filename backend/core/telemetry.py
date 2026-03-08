from __future__ import annotations

import logging
from typing import Any

try:  # pragma: no cover - optional instrumentation
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:  # pragma: no cover
    trace = None  # type: ignore

from backend.core.config import get_settings


log = logging.getLogger(__name__)
_configured = False


def configure_telemetry(app, engine: Any) -> None:
    global _configured
    if _configured:
        return
    if trace is None:
        log.warning("OpenTelemetry packages not installed; skipping instrumentation")
        return
    settings = get_settings()
    exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint, insecure=True)
    provider = TracerProvider(resource=Resource.create({"service.name": "ccf-backend"}))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    _configured = True
