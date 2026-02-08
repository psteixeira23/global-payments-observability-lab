from __future__ import annotations

from typing import Any

_MAX_HEADER_LENGTH = 128
_CURRENCY_CODE_LENGTH = 3


def _normalize_text(value: Any, *, field_name: str) -> str:
    if value is None or not isinstance(value, str):
        raise ValueError(f"Missing required {field_name}")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"Missing required {field_name}")
    return normalized


def require_header(headers: dict[str, Any], key: str) -> str:
    value = _normalize_text(headers.get(key), field_name=f"header: {key}")
    if len(value) > _MAX_HEADER_LENGTH:
        raise ValueError(f"Header too long: {key}")
    return value


def ensure_supported_currency(currency: str, supported: set[str]) -> str:
    normalized = _normalize_text(currency, field_name="currency").upper()
    if len(normalized) != _CURRENCY_CODE_LENGTH:
        raise ValueError(f"Invalid currency code length: {normalized}")
    supported_codes = {
        item.strip().upper() for item in supported if isinstance(item, str) and item.strip()
    }
    if normalized not in supported_codes:
        raise ValueError(f"Unsupported currency: {normalized}")
    return normalized
