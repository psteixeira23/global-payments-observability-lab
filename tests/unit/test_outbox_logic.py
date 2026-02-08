from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from payments_processor.providers.strategy import ProviderStrategyFactory
from payments_processor.workers import outbox_worker

from shared.contracts import PaymentMethod, ProviderResponse
from shared.contracts.enums import EventType
from shared.contracts.events import PaymentRequestedPayload


@dataclass
class FakePayment:
    payment_id: object
    merchant_id: str = "merchant-1"
    amount: Decimal = Decimal("10.00")
    currency: str = "BRL"
    method: PaymentMethod = PaymentMethod.PIX
    version: int = 1


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False


class FakeOutboxRepository:
    events = []

    def __init__(self, session: FakeSession) -> None:
        self._session = session
        self.pending = [
            SimpleNamespace(
                event_id=uuid4(),
                aggregate_id=PAYMENT.payment_id,
                payload={"traceparent": None},
                attempts=0,
            )
        ]
        self.sent: list[object] = []

    async def backlog_size(self) -> int:
        return len(self.pending)

    async def oldest_pending_lag_seconds(self) -> float:
        return 0.1

    async def fetch_pending_requested(self, limit: int):  # noqa: ARG002
        return self.pending

    async def mark_sent(self, event_id):  # noqa: ANN001
        self.sent.append(event_id)

    async def mark_failed(self, event_id, attempts):  # noqa: ANN001, ARG002
        self.sent.append(event_id)

    async def reschedule(self, event_id, attempts, delay_seconds):  # noqa: ANN001, ARG002
        self.sent.append(event_id)

    async def emit_event(self, aggregate_id, event_type, payload):  # noqa: ANN001
        self.events.append((aggregate_id, event_type, payload))


class FakePaymentRepository:
    def __init__(self, session: FakeSession) -> None:  # noqa: ARG002
        self.payment = PAYMENT

    async def get_by_id(self, payment_id):  # noqa: ANN001
        return self.payment if payment_id == self.payment.payment_id else None

    async def mark_processing(self, payment):  # noqa: ANN001
        return payment.payment_id == self.payment.payment_id

    async def mark_confirmed(self, payment):  # noqa: ANN001, ARG002
        return True

    async def mark_failed(self, payment, reason):  # noqa: ANN001, ARG002
        return True


class FakeProviderCommand:
    async def execute(self, payment):  # noqa: ANN001
        return ProviderResponse(
            provider_reference=f"pix-{payment.payment_id}",
            confirmed=True,
            provider="pix-provider",
            duplicate=False,
            partial_failure=False,
        )


PAYMENT = FakePayment(payment_id=uuid4())


def test_outbox_payload_serialization() -> None:
    payload = PaymentRequestedPayload(
        payment_id=PAYMENT.payment_id,
        merchant_id="merchant-1",
        trace_id="trace-1",
        traceparent="00-abc-def-01",
    ).model_dump(mode="json")

    assert payload["payment_id"]
    assert payload["trace_id"] == "trace-1"


@pytest.mark.asyncio
async def test_worker_polls_and_emits_confirmed_event(monkeypatch: pytest.MonkeyPatch) -> None:
    session = FakeSession()
    fake_outbox_repo = FakeOutboxRepository(session)

    monkeypatch.setattr(outbox_worker, "OutboxRepository", lambda _session: fake_outbox_repo)
    monkeypatch.setattr(outbox_worker, "PaymentRepository", FakePaymentRepository)

    settings = SimpleNamespace(
        poll_interval_seconds=0.01,
        batch_size=10,
        max_event_attempts=3,
    )

    worker = outbox_worker.OutboxWorker(
        settings=settings,
        session_factory=FakeSessionFactory(session),
        provider_command=FakeProviderCommand(),
        strategy_factory=ProviderStrategyFactory(),
    )

    await worker.run_once()

    assert len(fake_outbox_repo.sent) == 1
    aggregate_id, event_type, _payload = fake_outbox_repo.events[0]
    assert aggregate_id == PAYMENT.payment_id
    assert event_type == EventType.PAYMENT_CONFIRMED
