from __future__ import annotations

import pytest

from shared.utils.validation import ensure_supported_currency, require_header


def test_require_header_rejects_empty_value() -> None:
    with pytest.raises(ValueError):
        require_header({"Idempotency-Key": "   "}, "Idempotency-Key")


def test_ensure_supported_currency_normalizes_supported_codes() -> None:
    supported = {"brl", " usd "}
    assert ensure_supported_currency("brl", supported) == "BRL"


def test_ensure_supported_currency_rejects_invalid_length() -> None:
    with pytest.raises(ValueError):
        ensure_supported_currency("USDT", {"USD", "BRL"})
