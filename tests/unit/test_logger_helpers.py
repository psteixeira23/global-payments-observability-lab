from __future__ import annotations

import json
import logging

from shared.logging.logger import (
    JsonFormatter,
    clear_correlation_context,
    configure_logging,
    get_correlation_context,
    set_correlation_context,
    update_correlation_context,
)


def test_correlation_context_helpers_set_update_and_clear() -> None:
    clear_correlation_context()
    set_correlation_context({"merchant_id": "merchant-1"})
    update_correlation_context({"payment_id": "payment-1"})

    context = get_correlation_context()
    assert context == {"merchant_id": "merchant-1", "payment_id": "payment-1"}

    clear_correlation_context()
    assert get_correlation_context() == {}


def test_json_formatter_includes_exception_and_redacts_nested_card_data() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="payments",
        level=logging.ERROR,
        pathname=__file__,
        lineno=10,
        msg="failed for card 4111111111111111",
        args=(),
        exc_info=None,
    )
    try:
        raise ValueError("boom")
    except ValueError:
        record.exc_info = True, ValueError("boom"), None
    record.extra_fields = {
        "beneficiary": "sensitive-destination",
        "metadata": {"card_number": "4111111111111111", "tuple_values": ("a", "b")},
    }

    payload = json.loads(formatter.format(record))

    assert payload["beneficiary"] == "[REDACTED]"
    assert payload["metadata"]["card_number"] == "[REDACTED]"
    assert payload["metadata"]["tuple_values"] == ["a", "b"]
    assert "4111111111111111" not in payload["message"]
    assert "exception" in payload


def test_configure_logging_is_idempotent_when_root_has_handlers() -> None:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    try:
        root.handlers.clear()
        configure_logging("INFO")
        first_count = len(root.handlers)
        configure_logging("DEBUG")
        second_count = len(root.handlers)
    finally:
        root.handlers = original_handlers

    assert first_count == 1
    assert second_count == 1
