from __future__ import annotations

import json
import logging

from shared.logging.logger import JsonFormatter


def test_json_formatter_redacts_sensitive_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="card number 4111111111111111 should be hidden",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {
        "destination": "pix-key-123",
        "metadata": {"card_number": "4111111111111111", "plain": "ok"},
    }

    payload = json.loads(formatter.format(record))

    assert payload["destination"] == "[REDACTED]"
    assert payload["metadata"]["card_number"] == "[REDACTED]"
    assert "4111111111111111" not in payload["message"]


def test_json_formatter_handles_non_string_keys_and_deep_structures() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="ok",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {
        99: "numeric-key",
        "metadata": {"a": {"b": {"c": {"d": {"e": {"f": "too-deep"}}}}}},
    }

    payload = json.loads(formatter.format(record))

    assert payload["99"] == "numeric-key"
    assert payload["metadata"]["a"]["b"]["c"]["d"]["e"] == "[TRUNCATED]"
