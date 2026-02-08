from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from payments_processor.commands.finalize_payment import FinalizePaymentCommand

from shared.contracts import EventType


class FakePaymentRepository:
    def __init__(self) -> None:
        self.confirmed: object | None = None
        self.failed: tuple[object, str] | None = None

    async def mark_confirmed(self, payment):  # noqa: ANN001
        self.confirmed = payment

    async def mark_failed(self, payment, reason: str):  # noqa: ANN001
        self.failed = (payment, reason)


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    def emit_event(self, aggregate_id, event_type, payload):  # noqa: ANN001
        self.events.append((aggregate_id, event_type, payload))


def _payment() -> SimpleNamespace:
    return SimpleNamespace(payment_id=uuid4(), merchant_id="merchant-1")


@pytest.mark.asyncio
async def test_confirm_marks_payment_and_emits_confirmed_event() -> None:
    payment = _payment()
    payment_repository = FakePaymentRepository()
    outbox_repository = FakeOutboxRepository()
    command = FinalizePaymentCommand(payment_repository, outbox_repository)  # type: ignore[arg-type]

    await command.confirm(payment, provider="pix-provider", provider_reference="ref-1")

    assert payment_repository.confirmed is payment
    aggregate_id, event_type, payload = outbox_repository.events[0]
    assert aggregate_id == payment.payment_id
    assert event_type == EventType.PAYMENT_CONFIRMED
    assert payload["provider_reference"] == "ref-1"


@pytest.mark.asyncio
async def test_fail_marks_payment_and_emits_failed_event() -> None:
    payment = _payment()
    payment_repository = FakePaymentRepository()
    outbox_repository = FakeOutboxRepository()
    command = FinalizePaymentCommand(payment_repository, outbox_repository)  # type: ignore[arg-type]

    await command.fail(
        payment, provider="pix-provider", category="provider_5xx", reason="upstream_error"
    )

    assert payment_repository.failed == (payment, "upstream_error")
    aggregate_id, event_type, payload = outbox_repository.events[0]
    assert aggregate_id == payment.payment_id
    assert event_type == EventType.PAYMENT_FAILED
    assert payload["error_category"] == "provider_5xx"
