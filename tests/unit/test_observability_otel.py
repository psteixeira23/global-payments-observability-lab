from __future__ import annotations

from dataclasses import dataclass

from shared.observability import otel


@dataclass
class FakeTracerProvider:
    resource: object
    span_processors: list[object]

    def __init__(self, resource: object) -> None:
        self.resource = resource
        self.span_processors = []

    def add_span_processor(self, processor: object) -> None:
        self.span_processors.append(processor)


@dataclass
class FakeMeterProvider:
    resource: object
    metric_readers: list[object]

    def __init__(self, resource: object, metric_readers: list[object]) -> None:
        self.resource = resource
        self.metric_readers = metric_readers


def test_build_resource_uses_app_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_ENV", "ci")

    resource = otel._build_resource("svc-a")
    attributes = resource.attributes

    assert attributes["service.name"] == "svc-a"
    assert attributes["deployment.environment"] == "ci"


def test_configure_otel_is_idempotent_per_service_and_selects_exporters(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    otel._initialized_services.clear()
    calls: dict[str, list[object]] = {
        "trace_set": [],
        "metric_set": [],
        "trace_exporters": [],
        "metric_exporters": [],
    }

    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")
    monkeypatch.setenv("OTEL_METRICS_EXPORTER", "otlp")
    monkeypatch.setattr(otel, "TracerProvider", FakeTracerProvider)
    monkeypatch.setattr(otel, "MeterProvider", FakeMeterProvider)
    monkeypatch.setattr(otel, "OTLPSpanExporter", lambda: "otlp-trace")
    monkeypatch.setattr(otel, "ConsoleSpanExporter", lambda: "console-trace")
    monkeypatch.setattr(otel, "OTLPMetricExporter", lambda: "otlp-metric")
    monkeypatch.setattr(otel, "ConsoleMetricExporter", lambda: "console-metric")
    monkeypatch.setattr(
        otel,
        "BatchSpanProcessor",
        lambda exporter: calls["trace_exporters"].append(exporter) or ("span", exporter),
    )
    monkeypatch.setattr(
        otel,
        "PeriodicExportingMetricReader",
        lambda exporter: calls["metric_exporters"].append(exporter) or ("metric", exporter),
    )
    monkeypatch.setattr(
        otel.trace, "set_tracer_provider", lambda provider: calls["trace_set"].append(provider)
    )
    monkeypatch.setattr(
        otel.metrics, "set_meter_provider", lambda provider: calls["metric_set"].append(provider)
    )

    otel.configure_otel("svc-a")
    otel.configure_otel("svc-a")

    assert otel._initialized_services == {"svc-a"}
    assert calls["trace_exporters"] == ["otlp-trace"]
    assert calls["metric_exporters"] == ["otlp-metric"]
    assert len(calls["trace_set"]) == 1
    assert len(calls["metric_set"]) == 1


def test_configure_otel_uses_console_exporters_by_default(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    otel._initialized_services.clear()
    calls: dict[str, list[object]] = {"trace_exporters": [], "metric_exporters": []}

    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.delenv("OTEL_METRICS_EXPORTER", raising=False)
    monkeypatch.setattr(otel, "TracerProvider", FakeTracerProvider)
    monkeypatch.setattr(otel, "MeterProvider", FakeMeterProvider)
    monkeypatch.setattr(otel, "OTLPSpanExporter", lambda: "otlp-trace")
    monkeypatch.setattr(otel, "ConsoleSpanExporter", lambda: "console-trace")
    monkeypatch.setattr(otel, "OTLPMetricExporter", lambda: "otlp-metric")
    monkeypatch.setattr(otel, "ConsoleMetricExporter", lambda: "console-metric")
    monkeypatch.setattr(
        otel,
        "BatchSpanProcessor",
        lambda exporter: calls["trace_exporters"].append(exporter) or ("span", exporter),
    )
    monkeypatch.setattr(
        otel,
        "PeriodicExportingMetricReader",
        lambda exporter: calls["metric_exporters"].append(exporter) or ("metric", exporter),
    )
    monkeypatch.setattr(otel.trace, "set_tracer_provider", lambda _provider: None)
    monkeypatch.setattr(otel.metrics, "set_meter_provider", lambda _provider: None)

    otel.configure_otel("svc-b")

    assert calls["trace_exporters"] == ["console-trace"]
    assert calls["metric_exporters"] == ["console-metric"]
