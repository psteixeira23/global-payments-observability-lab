from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from numbers import Number
from typing import Any

_correlation_ctx: ContextVar[dict[str, str] | None] = ContextVar("correlation_ctx", default=None)
_CARD_LIKE_PATTERN = re.compile(r"\b\d{12,19}\b")
_REDACTED_FIELDS = {
    "destination",
    "pix_key",
    "beneficiary",
    "card_number",
    "pan",
}
_MAX_SANITIZE_DEPTH = 6


def _redact_string(value: str) -> str:
    return _CARD_LIKE_PATTERN.sub("[REDACTED]", value)


def _sanitize_mapping(values: dict[str, Any], depth: int) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in values.items():
        key_text = str(key)
        key_lower = key_text.lower()
        if key_lower in _REDACTED_FIELDS:
            sanitized[key_text] = "[REDACTED]"
            continue
        sanitized[key_text] = _sanitize_value(value, depth + 1)
    return sanitized


def _sanitize_sequence(values: list[Any], depth: int) -> list[Any]:
    return [_sanitize_value(item, depth + 1) for item in values]


def _sanitize_value(value: Any, depth: int = 0) -> Any:
    if depth >= _MAX_SANITIZE_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return _sanitize_mapping(value, depth)
    if isinstance(value, list):
        return _sanitize_sequence(value, depth)
    if isinstance(value, tuple):
        return tuple(_sanitize_sequence(list(value), depth))
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, Number | bool) or value is None:
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact_string(record.getMessage()),
        }
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)
        base.update(_current_correlation_context())
        if hasattr(record, "extra_fields"):
            base.update(record.extra_fields)
        return json.dumps(_sanitize_value(base), default=str)


def _current_correlation_context() -> dict[str, str]:
    return _correlation_ctx.get() or {}


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def set_correlation_context(values: dict[str, str]) -> None:
    _correlation_ctx.set(dict(values))


def update_correlation_context(values: dict[str, str]) -> None:
    merged = dict(_current_correlation_context())
    merged.update(values)
    _correlation_ctx.set(merged)


def get_correlation_context() -> dict[str, str]:
    return dict(_current_correlation_context())


def clear_correlation_context() -> None:
    _correlation_ctx.set({})


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
