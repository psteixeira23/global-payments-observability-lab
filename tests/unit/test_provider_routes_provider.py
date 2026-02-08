from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from provider_mock.api import routes_provider

from shared.contracts import PaymentMethod, ProviderResponse
from tests.helpers import (
    FakeProviderEngine,
    build_app_with_router,
    make_provider_request_payload,
    override_dependencies,
)


@pytest.fixture
def provider_client() -> Iterator[TestClient]:
    app = build_app_with_router(routes_provider.router)
    with TestClient(app) as client:
        yield client


def test_get_engine_reads_engine_from_app_state(provider_client: TestClient) -> None:
    expected_engine = FakeProviderEngine()
    provider_client.app.state.engine = expected_engine

    request = SimpleNamespace(app=provider_client.app)
    assert routes_provider.get_engine(request) is expected_engine  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("method", "path", "expected_provider"),
    [
        (PaymentMethod.PIX, "/providers/pix/confirm", "pix-provider"),
        (PaymentMethod.BOLETO, "/providers/boleto/confirm", "boleto-provider"),
        (PaymentMethod.TED, "/providers/ted/confirm", "ted-provider"),
        (PaymentMethod.CARD, "/providers/card/confirm", "card-provider"),
    ],
)
def test_provider_routes_return_schema_with_expected_provider(
    provider_client: TestClient,
    method: PaymentMethod,
    path: str,
    expected_provider: str,
) -> None:
    fake_engine = FakeProviderEngine(
        response=ProviderResponse(
            provider_reference=f"{method.value.lower()}-ref",
            confirmed=True,
            provider=expected_provider,
            duplicate=False,
            partial_failure=False,
        )
    )
    with override_dependencies(
        provider_client.app, {routes_provider.get_engine: lambda: fake_engine}
    ):
        response = provider_client.post(path, json=make_provider_request_payload(method=method))

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == expected_provider
    assert payload["confirmed"] is True


def test_provider_route_maps_timeout_to_504(provider_client: TestClient) -> None:
    with override_dependencies(
        provider_client.app,
        {routes_provider.get_engine: lambda: FakeProviderEngine(error=TimeoutError("timeout"))},
    ):
        response = provider_client.post(
            "/providers/pix/confirm",
            json=make_provider_request_payload(method=PaymentMethod.PIX),
        )

    assert response.status_code == 504
    assert response.json()["detail"] == "Provider timeout"


def test_provider_route_maps_runtime_error_to_503(provider_client: TestClient) -> None:
    with override_dependencies(
        provider_client.app,
        {routes_provider.get_engine: lambda: FakeProviderEngine(error=RuntimeError("down"))},
    ):
        response = provider_client.post(
            "/providers/pix/confirm",
            json=make_provider_request_payload(method=PaymentMethod.PIX),
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Provider unavailable"


def test_provider_route_validates_request_body(provider_client: TestClient) -> None:
    with override_dependencies(
        provider_client.app,
        {routes_provider.get_engine: lambda: FakeProviderEngine()},
    ):
        response = provider_client.post(
            "/providers/pix/confirm", json={"merchant_id": "merchant-1"}
        )

    assert response.status_code == 422
