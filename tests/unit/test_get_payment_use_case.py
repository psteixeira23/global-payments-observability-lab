from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from payments_api.core.errors import ValidationAppError
from payments_api.use_cases import get_payment

from shared.contracts import AmlDecision, PaymentMethod, PaymentStatus, RiskDecision


class FakeSessionFactory:
    def __init__(self, session: object) -> None:
        self._session = session

    def __call__(self) -> FakeSessionFactory:
        return self

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


class FakePaymentRepository:
    def __init__(self, payment: object | None) -> None:
        self._payment = payment
        self.requested_payment_id = None

    async def get_by_payment_id(self, payment_id):  # noqa: ANN001
        self.requested_payment_id = payment_id
        return self._payment


def _payment_entity() -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        payment_id=uuid4(),
        merchant_id="merchant-1",
        customer_id="customer-1",
        account_id="account-1",
        amount=Decimal("10.50"),
        currency="BRL",
        method=PaymentMethod.PIX,
        status=PaymentStatus.RECEIVED,
        idempotency_key="idem-1",
        risk_score=15,
        risk_decision=RiskDecision.ALLOW,
        aml_decision=AmlDecision.ALLOW,
        created_at=now,
        updated_at=now,
        last_error=None,
    )


@pytest.mark.asyncio
async def test_get_payment_returns_status_response_when_payment_exists(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payment = _payment_entity()
    repository = FakePaymentRepository(payment)
    use_case = get_payment.GetPaymentUseCase(FakeSessionFactory(object()))  # type: ignore[arg-type]
    monkeypatch.setattr(get_payment, "PaymentRepository", lambda _session: repository)

    response = await use_case.execute(payment.payment_id)

    assert repository.requested_payment_id == payment.payment_id
    assert response.payment_id == payment.payment_id
    assert response.amount == Decimal("10.50")
    assert response.status == PaymentStatus.RECEIVED
    assert response.risk_decision == RiskDecision.ALLOW
    assert response.aml_decision == AmlDecision.ALLOW


@pytest.mark.asyncio
async def test_get_payment_raises_validation_error_when_payment_does_not_exist(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    repository = FakePaymentRepository(None)
    use_case = get_payment.GetPaymentUseCase(FakeSessionFactory(object()))  # type: ignore[arg-type]
    monkeypatch.setattr(get_payment, "PaymentRepository", lambda _session: repository)

    with pytest.raises(ValidationAppError, match="Payment not found"):
        await use_case.execute(uuid4())
