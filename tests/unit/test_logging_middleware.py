from __future__ import annotations

from fastapi import FastAPI

from shared.logging import CorrelationMiddleware, get_correlation_context
from tests.helpers import create_test_client


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.get("/echo")
    def echo_context() -> dict[str, str]:
        return get_correlation_context()

    @app.get("/boom")
    def raise_error() -> None:
        raise RuntimeError("forced")

    return app


def test_correlation_middleware_enriches_context_from_headers() -> None:
    app = _build_app()
    headers = {
        "Idempotency-Key": "idem-1",
        "X-Merchant-Id": "merchant-1",
        "X-Customer-Id": "customer-1",
        "X-Account-Id": "account-1",
        "X-Rail": "PIX",
    }

    with create_test_client(app) as client:
        response = client.get("/echo", headers=headers)

    payload = response.json()
    assert response.status_code == 200
    assert payload["idempotency_key"] == "idem-1"
    assert payload["merchant_id"] == "merchant-1"
    assert payload["customer_id"] == "customer-1"
    assert payload["account_id"] == "account-1"
    assert payload["rail"] == "PIX"
    assert "trace_id" in payload
    assert get_correlation_context() == {}


def test_correlation_middleware_clears_context_even_when_handler_fails() -> None:
    app = _build_app()
    with create_test_client(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert get_correlation_context() == {}
