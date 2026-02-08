from __future__ import annotations

from typing import Any


def assert_error_payload(
    response: Any,
    *,
    expected_status: int,
    expected_category: str,
) -> None:
    payload = response.json()
    assert response.status_code == expected_status
    assert payload["error"]["category"] == expected_category
    assert isinstance(payload["error"]["message"], str)
