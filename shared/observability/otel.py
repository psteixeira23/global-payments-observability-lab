from __future__ import annotations

import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_initialized_services: set[str] = set()


def _build_resource(service_name: str) -> Resource:
    return Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": os.getenv("APP_ENV", "local"),
        }
    )


def configure_otel(service_name: str) -> None:
    if service_name in _initialized_services:
        return

    resource = _build_resource(service_name)

    tracer_provider = TracerProvider(resource=resource)
    trace_exporter_mode = os.getenv("OTEL_TRACES_EXPORTER", "console")
    if trace_exporter_mode == "otlp":
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    else:
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    metric_exporter_mode = os.getenv("OTEL_METRICS_EXPORTER", "console")
    if metric_exporter_mode == "otlp":
        metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    else:
        metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    _initialized_services.add(service_name)
