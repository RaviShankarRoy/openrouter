"""OpenTelemetry bootstrapping. Auto-instruments FastAPI + SQLAlchemy."""
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.shared.config import Settings


def init_tracing(settings: Settings) -> None:
    if not settings.otel_exporter_otlp_endpoint:
        return
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.service_version,
            "deployment.environment": settings.environment,
        }
    )
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(settings.otel_traces_sampler_arg)),
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
    )
    trace.set_tracer_provider(provider)
