from __future__ import annotations

from collections.abc import Mapping

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.propagate import extract, inject


def inject_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    carrier: dict[str, str] = headers or {}
    inject(carrier)
    return carrier


def extract_context_from_headers(headers: Mapping[str, str]) -> Context:
    return extract(dict(headers))


def current_trace_id() -> str:
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if not span_context.is_valid:
        return ""
    return format(span_context.trace_id, "032x")


def current_traceparent() -> str | None:
    carrier: dict[str, str] = {}
    inject(carrier)
    return carrier.get("traceparent")
