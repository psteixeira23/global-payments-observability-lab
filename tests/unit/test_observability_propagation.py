from __future__ import annotations

from types import SimpleNamespace

from shared.observability import propagation


def test_inject_headers_returns_augmented_carrier(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_inject(carrier: dict[str, str]) -> None:
        carrier["traceparent"] = "00-abc-def-01"

    monkeypatch.setattr(propagation, "inject", fake_inject)

    headers = propagation.inject_headers({"Content-Type": "application/json"})

    assert headers["Content-Type"] == "application/json"
    assert headers["traceparent"] == "00-abc-def-01"


def test_extract_context_from_headers_delegates_to_extractor(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, str] = {}

    def fake_extract(carrier: dict[str, str]) -> str:
        captured.update(carrier)
        return "ctx"

    monkeypatch.setattr(propagation, "extract", fake_extract)

    result = propagation.extract_context_from_headers({"traceparent": "00-abc-def-01"})

    assert result == "ctx"
    assert captured == {"traceparent": "00-abc-def-01"}


def test_current_trace_id_returns_empty_when_span_context_is_invalid(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    span = SimpleNamespace(get_span_context=lambda: SimpleNamespace(is_valid=False, trace_id=0))
    monkeypatch.setattr(propagation.trace, "get_current_span", lambda: span)

    assert propagation.current_trace_id() == ""


def test_current_trace_id_formats_valid_trace_id(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    span = SimpleNamespace(
        get_span_context=lambda: SimpleNamespace(is_valid=True, trace_id=0xABCDEF1234)
    )
    monkeypatch.setattr(propagation.trace, "get_current_span", lambda: span)

    trace_id = propagation.current_trace_id()

    assert len(trace_id) == 32
    assert trace_id.endswith("abcdef1234")


def test_current_traceparent_reads_value_from_injected_carrier(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        propagation,
        "inject",
        lambda carrier: carrier.update({"traceparent": "00-abc-def-01"}),
    )

    assert propagation.current_traceparent() == "00-abc-def-01"
