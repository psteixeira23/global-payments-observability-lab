from __future__ import annotations

from fastapi import FastAPI
from payments_api.core.error_handlers import register_error_handlers
from payments_api.core.errors import ValidationAppError

from tests.helpers import assert_error_payload, create_test_client


def _build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/app-error")
    def app_error_route() -> None:
        raise ValidationAppError("Invalid payment input")

    @app.get("/unexpected-error")
    def unexpected_error_route() -> None:
        raise RuntimeError("raw stack detail")

    return app


def test_app_error_handler_returns_standard_error_contract() -> None:
    app = _build_app()
    with create_test_client(app) as client:
        response = client.get("/app-error")

    assert_error_payload(
        response,
        expected_status=422,
        expected_category="validation_error",
    )
    assert response.json()["error"]["message"] == "Invalid payment input"


def test_unexpected_error_handler_masks_internal_details() -> None:
    app = _build_app()
    with create_test_client(app, raise_server_exceptions=False) as client:
        response = client.get("/unexpected-error")

    assert_error_payload(
        response,
        expected_status=500,
        expected_category="unexpected",
    )
    assert response.json()["error"]["message"] == "Internal server error"
