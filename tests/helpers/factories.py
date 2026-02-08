from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from shared.contracts import (
    AmlDecision,
    PaymentAcceptedResponse,
    PaymentMethod,
    PaymentStatus,
    PaymentStatusResponse,
    RiskDecision,
)


def make_create_payment_payload(
    *,
    amount: str = "10.00",
    currency: str = "BRL",
    method: PaymentMethod = PaymentMethod.PIX,
    destination: str | None = "dest-1",
) -> dict[str, str | float | None]:
    return {
        "amount": float(amount),
        "currency": currency,
        "method": method.value,
        "destination": destination,
    }


def make_provider_request_payload(
    *,
    method: PaymentMethod = PaymentMethod.PIX,
    amount: str = "10.00",
) -> dict[str, str | float]:
    return {
        "payment_id": str(uuid4()),
        "merchant_id": "merchant-1",
        "amount": float(amount),
        "currency": "BRL",
        "method": method.value,
    }


def make_payment_accepted_response(
    *,
    status: PaymentStatus = PaymentStatus.RECEIVED,
    risk_decision: RiskDecision = RiskDecision.ALLOW,
    aml_decision: AmlDecision = AmlDecision.ALLOW,
) -> PaymentAcceptedResponse:
    return PaymentAcceptedResponse(
        payment_id=uuid4(),
        status=status,
        trace_id="trace-123",
        risk_decision=risk_decision,
        aml_decision=aml_decision,
    )


def make_payment_status_response(
    *,
    status: PaymentStatus = PaymentStatus.RECEIVED,
    method: PaymentMethod = PaymentMethod.PIX,
) -> PaymentStatusResponse:
    now = datetime.now(UTC)
    return PaymentStatusResponse(
        payment_id=uuid4(),
        merchant_id="merchant-1",
        customer_id="customer-1",
        account_id="account-1",
        amount=Decimal("10.00"),
        currency="BRL",
        method=method,
        status=status,
        idempotency_key="idem-1",
        risk_score=10,
        risk_decision=RiskDecision.ALLOW,
        aml_decision=AmlDecision.ALLOW,
        created_at=now,
        updated_at=now,
        last_error=None,
    )


def make_review_payment(*, status: PaymentStatus = PaymentStatus.IN_REVIEW) -> SimpleNamespace:
    return SimpleNamespace(
        payment_id=uuid4(),
        merchant_id="merchant-1",
        status=status,
        risk_decision=RiskDecision.REVIEW,
        aml_decision=AmlDecision.ALLOW,
    )
