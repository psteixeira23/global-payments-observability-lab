from __future__ import annotations

from fastapi import Response

from shared.utils import SECURITY_HEADERS, apply_security_headers


def test_apply_security_headers_sets_default_headers() -> None:
    response = Response()
    apply_security_headers(response)

    for key, expected_value in SECURITY_HEADERS.items():
        assert response.headers[key] == expected_value


def test_apply_security_headers_does_not_override_existing_header() -> None:
    response = Response(headers={"X-Frame-Options": "SAMEORIGIN"})
    apply_security_headers(response)

    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
