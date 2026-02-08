from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from payments_api.core.errors import ValidationAppError
from payments_api.use_cases import review_payment

from shared.contracts import PaymentStatus
from tests.helpers import (
    FakeOutboxRepository,
    FakePaymentRepository,
    FakeSession,
    FakeSessionFactory,
    make_review_payment,
)


@pytest.fixture
def review_context() -> Iterator[dict[str, object]]:
    session = FakeSession()
    payment = make_review_payment()
    payments = FakePaymentRepository(payment)
    outbox = FakeOutboxRepository()
    yield {"session": session, "payment": payment, "payments": payments, "outbox": outbox}


@pytest.mark.asyncio
async def test_approve_review_updates_status_and_emits_event(
    monkeypatch: pytest.MonkeyPatch,
    review_context: dict[str, object],
) -> None:
    session = review_context["session"]
    payment = review_context["payment"]
    payments = review_context["payments"]
    outbox = review_context["outbox"]

    monkeypatch.setattr(review_payment, "PaymentRepository", lambda _session: payments)
    monkeypatch.setattr(review_payment, "OutboxRepository", lambda _session: outbox)

    use_case = review_payment.ApproveReviewPaymentUseCase(FakeSessionFactory(session))  # type: ignore[arg-type]
    response = await use_case.execute(payment.payment_id)  # type: ignore[attr-defined]

    assert response.status == PaymentStatus.RECEIVED
    assert payments.updated == (payment.payment_id, PaymentStatus.RECEIVED, None)  # type: ignore[attr-defined]
    assert len(outbox.events) == 1  # type: ignore[attr-defined]
    assert session.commits == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_reject_review_updates_status_with_reason(
    monkeypatch: pytest.MonkeyPatch,
    review_context: dict[str, object],
) -> None:
    session = review_context["session"]
    payment = review_context["payment"]
    payments = review_context["payments"]

    monkeypatch.setattr(review_payment, "PaymentRepository", lambda _session: payments)

    use_case = review_payment.RejectReviewPaymentUseCase(FakeSessionFactory(session))  # type: ignore[arg-type]
    response = await use_case.execute(payment.payment_id)  # type: ignore[attr-defined]

    assert response.status == PaymentStatus.BLOCKED
    assert payments.updated is not None  # type: ignore[attr-defined]
    assert payments.updated[0] == payment.payment_id  # type: ignore[attr-defined]
    assert payments.updated[1] == PaymentStatus.BLOCKED  # type: ignore[attr-defined]
    assert payments.updated[2] == "manual_review_rejected"  # type: ignore[attr-defined]
    assert session.commits == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_approve_review_raises_when_payment_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    payments = FakePaymentRepository(payment=None)
    monkeypatch.setattr(review_payment, "PaymentRepository", lambda _session: payments)

    use_case = review_payment.ApproveReviewPaymentUseCase(FakeSessionFactory(session))  # type: ignore[arg-type]
    with pytest.raises(ValidationAppError, match="Payment not found"):
        await use_case.execute(uuid4())


@pytest.mark.asyncio
async def test_reject_review_raises_when_payment_status_is_not_in_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    payment = make_review_payment(status=PaymentStatus.RECEIVED)
    payments = FakePaymentRepository(payment=payment)
    monkeypatch.setattr(review_payment, "PaymentRepository", lambda _session: payments)

    use_case = review_payment.RejectReviewPaymentUseCase(FakeSessionFactory(session))  # type: ignore[arg-type]
    with pytest.raises(ValidationAppError, match="Payment is not in review"):
        await use_case.execute(payment.payment_id)  # type: ignore[attr-defined]
