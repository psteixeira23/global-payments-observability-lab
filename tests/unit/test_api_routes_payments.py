from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from payments_api.api import dependencies
from payments_api.api.routes_payments import router

from shared.contracts import PaymentStatus
from tests.helpers import (
    FakeCreatePaymentUseCase,
    FakeGetPaymentUseCase,
    FakeReviewUseCase,
    build_app_with_router,
    make_create_payment_payload,
    make_payment_accepted_response,
    make_payment_status_response,
    override_dependencies,
)


@pytest.fixture
def payments_client() -> Iterator[TestClient]:
    create_use_case = FakeCreatePaymentUseCase(make_payment_accepted_response())
    get_use_case = FakeGetPaymentUseCase(make_payment_status_response())
    approve_use_case = FakeReviewUseCase(
        make_payment_accepted_response(status=PaymentStatus.RECEIVED)
    )
    reject_use_case = FakeReviewUseCase(
        make_payment_accepted_response(status=PaymentStatus.BLOCKED)
    )

    app = build_app_with_router(router)
    with override_dependencies(
        app,
        {
            dependencies.get_create_payment_use_case: lambda: create_use_case,
            dependencies.get_get_payment_use_case: lambda: get_use_case,
            dependencies.get_approve_review_use_case: lambda: approve_use_case,
            dependencies.get_reject_review_use_case: lambda: reject_use_case,
        },
    ):
        app.state.create_use_case = create_use_case
        app.state.get_use_case = get_use_case
        app.state.approve_use_case = approve_use_case
        app.state.reject_use_case = reject_use_case
        with TestClient(app) as client:
            yield client


def _required_headers() -> dict[str, str]:
    return {
        "Idempotency-Key": "idem-1",
        "X-Merchant-Id": "merchant-1",
        "X-Customer-Id": "customer-1",
        "X-Account-Id": "account-1",
    }


def test_create_payment_route_maps_headers_and_returns_202(payments_client: TestClient) -> None:
    response = payments_client.post(
        "/payments",
        headers=_required_headers(),
        json=make_create_payment_payload(),
    )

    assert response.status_code == 202
    assert response.json()["status"] == "RECEIVED"
    assert payments_client.app.state.create_use_case.headers == {
        "Idempotency-Key": "idem-1",
        "X-Merchant-Id": "merchant-1",
        "X-Customer-Id": "customer-1",
        "X-Account-Id": "account-1",
        "X-Rail": "PIX",
    }


def test_create_payment_route_validates_required_headers(payments_client: TestClient) -> None:
    response = payments_client.post("/payments", json=make_create_payment_payload())
    assert response.status_code == 422


def test_get_payment_route_delegates_to_use_case(payments_client: TestClient) -> None:
    payment_id = uuid4()
    response = payments_client.get(f"/payments/{payment_id}")

    assert response.status_code == 200
    assert payments_client.app.state.get_use_case.payment_id == payment_id
    assert response.json()["status"] == "RECEIVED"


def test_approve_review_route_delegates_to_use_case(payments_client: TestClient) -> None:
    payment_id = uuid4()
    response = payments_client.post(f"/review/{payment_id}/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "RECEIVED"
    assert payments_client.app.state.approve_use_case.payment_id == payment_id


def test_reject_review_route_delegates_to_use_case(payments_client: TestClient) -> None:
    payment_id = uuid4()
    response = payments_client.post(f"/review/{payment_id}/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "BLOCKED"
    assert payments_client.app.state.reject_use_case.payment_id == payment_id
