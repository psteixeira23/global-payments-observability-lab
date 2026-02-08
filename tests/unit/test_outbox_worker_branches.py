from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from payments_processor.core.errors import ProviderTimeoutError
from payments_processor.workers import outbox_worker

from shared.contracts import PaymentFailureReason, PaymentMethod, ProviderName, ProviderResponse


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self) -> FakeSessionFactory:
        return self

    async def __aenter__(self) -> FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


class FakeOutboxRepository:
    def __init__(self, _session: FakeSession, event: object) -> None:
        self._event = event
        self.failed: list[tuple[object, int]] = []
        self.sent: list[object] = []
        self.rescheduled: list[tuple[object, int, float]] = []
        self.backlog_queries = 0
        self.lag_queries = 0

    async def backlog_size(self) -> int:
        self.backlog_queries += 1
        return 1

    async def oldest_pending_lag_seconds(self) -> float:
        self.lag_queries += 1
        return 0.5

    async def fetch_pending_requested(self, _limit: int) -> list[object]:
        return [self._event]

    async def mark_failed(self, event_id, attempts: int) -> None:  # noqa: ANN001
        self.failed.append((event_id, attempts))

    async def mark_sent(self, event_id) -> None:  # noqa: ANN001
        self.sent.append(event_id)

    async def reschedule(
        self, event_id, attempts: int, delay_seconds: float
    ) -> None:  # noqa: ANN001
        self.rescheduled.append((event_id, attempts, delay_seconds))

    def emit_event(self, aggregate_id, event_type, payload) -> None:  # noqa: ANN001, ARG002
        return None


class FakePaymentRepository:
    def __init__(
        self, _session: FakeSession, *, payment: object | None, mark_processing_ok: bool
    ) -> None:
        self._payment = payment
        self._mark_processing_ok = mark_processing_ok

    async def get_by_id(self, _payment_id):  # noqa: ANN001
        return self._payment

    async def mark_processing(self, _payment: object) -> bool:
        return self._mark_processing_ok

    async def mark_confirmed(self, _payment: object) -> bool:
        return True

    async def mark_failed(self, _payment: object, _reason: str) -> bool:
        return True


class FakeFinalizeCommand:
    def __init__(self, _payment_repo, _outbox_repo) -> None:  # noqa: ANN001
        self.confirm_calls: list[tuple] = []
        self.fail_calls: list[tuple] = []

    async def confirm(
        self, payment, provider: str, provider_reference: str
    ) -> None:  # noqa: ANN001
        self.confirm_calls.append((payment, provider, provider_reference))

    async def fail(
        self, payment, provider: str, category: str, reason: str
    ) -> None:  # noqa: ANN001
        self.fail_calls.append((payment, provider, category, reason))


class FakeProviderCommand:
    def __init__(
        self, response: ProviderResponse | None = None, error: Exception | None = None
    ) -> None:
        self._response = response
        self._error = error

    async def execute(self, _payment: object) -> ProviderResponse:
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


def _payment() -> SimpleNamespace:
    return SimpleNamespace(
        payment_id=uuid4(),
        merchant_id="merchant-1",
        amount="10.00",
        currency="BRL",
        method=PaymentMethod.PIX,
        version=1,
    )


def _event(payment_id, attempts: int = 0, traceparent: str | None = None):  # noqa: ANN001
    return SimpleNamespace(
        event_id=uuid4(),
        aggregate_id=payment_id,
        payload={"traceparent": traceparent},
        attempts=attempts,
    )


def _worker(
    session: FakeSession,
    provider_command: object,
) -> outbox_worker.OutboxWorker:
    settings = SimpleNamespace(
        poll_interval_seconds=0.01,
        batch_size=10,
        max_event_attempts=3,
    )
    return outbox_worker.OutboxWorker(
        settings=settings,
        session_factory=FakeSessionFactory(session),  # type: ignore[arg-type]
        provider_command=provider_command,  # type: ignore[arg-type]
        strategy_factory=SimpleNamespace(for_method=lambda _method: SimpleNamespace(provider_name="pix-provider")),  # type: ignore[arg-type]
    )


def test_extract_context_builds_context_from_traceparent(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    session = FakeSession()
    worker = _worker(session, FakeProviderCommand(response=None))  # type: ignore[arg-type]
    expected_context = object()
    event = _event(uuid4(), traceparent="00-abc-def-01")

    monkeypatch.setattr(
        outbox_worker, "extract_context_from_headers", lambda headers: expected_context
    )

    result = worker._extract_context(event)

    assert result is expected_context


@pytest.mark.asyncio
async def test_worker_marks_event_failed_when_payment_is_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payment = _payment()
    event = _event(payment.payment_id)
    session = FakeSession()
    outbox_repo = FakeOutboxRepository(session, event)
    finalize = FakeFinalizeCommand(None, None)

    monkeypatch.setattr(outbox_worker, "OutboxRepository", lambda _session: outbox_repo)
    monkeypatch.setattr(
        outbox_worker,
        "PaymentRepository",
        lambda _session: FakePaymentRepository(_session, payment=None, mark_processing_ok=True),
    )
    monkeypatch.setattr(outbox_worker, "FinalizePaymentCommand", lambda _p, _o: finalize)
    monkeypatch.setattr(outbox_worker.outbox_backlog, "record", lambda *_: None)
    monkeypatch.setattr(outbox_worker.outbox_lag_seconds, "record", lambda *_: None)

    worker = _worker(session, FakeProviderCommand(response=None))  # type: ignore[arg-type]
    await worker.run_once()

    assert len(outbox_repo.failed) == 1
    assert outbox_repo.failed[0][1] == 1
    assert session.commits == 1
    assert finalize.confirm_calls == []


@pytest.mark.asyncio
async def test_worker_marks_sent_when_optimistic_lock_fails(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payment = _payment()
    event = _event(payment.payment_id)
    session = FakeSession()
    outbox_repo = FakeOutboxRepository(session, event)
    finalize = FakeFinalizeCommand(None, None)

    monkeypatch.setattr(outbox_worker, "OutboxRepository", lambda _session: outbox_repo)
    monkeypatch.setattr(
        outbox_worker,
        "PaymentRepository",
        lambda _session: FakePaymentRepository(_session, payment=payment, mark_processing_ok=False),
    )
    monkeypatch.setattr(outbox_worker, "FinalizePaymentCommand", lambda _p, _o: finalize)
    monkeypatch.setattr(outbox_worker.outbox_backlog, "record", lambda *_: None)
    monkeypatch.setattr(outbox_worker.outbox_lag_seconds, "record", lambda *_: None)

    worker = _worker(session, FakeProviderCommand(response=None))  # type: ignore[arg-type]
    await worker.run_once()

    assert outbox_repo.sent == [event.event_id]
    assert session.commits == 1
    assert finalize.confirm_calls == []
    assert finalize.fail_calls == []


@pytest.mark.asyncio
async def test_worker_handles_partial_failure_as_failed_payment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payment = _payment()
    event = _event(payment.payment_id)
    session = FakeSession()
    outbox_repo = FakeOutboxRepository(session, event)
    finalize = FakeFinalizeCommand(None, None)
    provider_response = ProviderResponse(
        provider_reference="pix-ref",
        confirmed=True,
        provider="pix-provider",
        duplicate=False,
        partial_failure=True,
    )

    monkeypatch.setattr(outbox_worker, "OutboxRepository", lambda _session: outbox_repo)
    monkeypatch.setattr(
        outbox_worker,
        "PaymentRepository",
        lambda _session: FakePaymentRepository(_session, payment=payment, mark_processing_ok=True),
    )
    monkeypatch.setattr(outbox_worker, "FinalizePaymentCommand", lambda _p, _o: finalize)
    monkeypatch.setattr(outbox_worker.outbox_backlog, "record", lambda *_: None)
    monkeypatch.setattr(outbox_worker.outbox_lag_seconds, "record", lambda *_: None)

    worker = _worker(session, FakeProviderCommand(response=provider_response))
    await worker.run_once()

    assert outbox_repo.sent == [event.event_id]
    assert session.commits == 1
    assert finalize.confirm_calls == []
    assert len(finalize.fail_calls) == 1
    assert finalize.fail_calls[0][2] == PaymentFailureReason.PROVIDER_PARTIAL_FAILURE.value


@pytest.mark.asyncio
async def test_worker_reschedules_transient_processor_error_before_max_attempts(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    payment = _payment()
    event = _event(payment.payment_id, attempts=1)
    session = FakeSession()
    outbox_repo = FakeOutboxRepository(session, event)
    finalize = FakeFinalizeCommand(None, None)

    monkeypatch.setattr(outbox_worker, "OutboxRepository", lambda _session: outbox_repo)
    monkeypatch.setattr(
        outbox_worker,
        "PaymentRepository",
        lambda _session: FakePaymentRepository(_session, payment=payment, mark_processing_ok=True),
    )
    monkeypatch.setattr(outbox_worker, "FinalizePaymentCommand", lambda _p, _o: finalize)
    monkeypatch.setattr(outbox_worker, "exponential_backoff", lambda *_args, **_kwargs: 0.5)
    monkeypatch.setattr(outbox_worker.outbox_backlog, "record", lambda *_: None)
    monkeypatch.setattr(outbox_worker.outbox_lag_seconds, "record", lambda *_: None)

    worker = _worker(session, FakeProviderCommand(error=ProviderTimeoutError("timeout")))
    await worker.run_once()

    assert outbox_repo.rescheduled == [(event.event_id, 2, 0.5)]
    assert finalize.fail_calls == []
    assert session.commits == 1


@pytest.mark.asyncio
async def test_worker_marks_failed_after_reaching_max_attempts(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payment = _payment()
    event = _event(payment.payment_id, attempts=2)
    session = FakeSession()
    outbox_repo = FakeOutboxRepository(session, event)
    finalize = FakeFinalizeCommand(None, None)

    monkeypatch.setattr(outbox_worker, "OutboxRepository", lambda _session: outbox_repo)
    monkeypatch.setattr(
        outbox_worker,
        "PaymentRepository",
        lambda _session: FakePaymentRepository(_session, payment=payment, mark_processing_ok=True),
    )
    monkeypatch.setattr(outbox_worker, "FinalizePaymentCommand", lambda _p, _o: finalize)
    monkeypatch.setattr(outbox_worker.outbox_backlog, "record", lambda *_: None)
    monkeypatch.setattr(outbox_worker.outbox_lag_seconds, "record", lambda *_: None)

    worker = _worker(session, FakeProviderCommand(error=ProviderTimeoutError("timeout")))
    await worker.run_once()

    assert outbox_repo.failed == [(event.event_id, 3)]
    assert len(finalize.fail_calls) == 1
    assert finalize.fail_calls[0][1] == "pix-provider"
    assert finalize.fail_calls[0][2] == "provider_timeout"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_worker_handles_unexpected_exception_with_unknown_provider(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payment = _payment()
    event = _event(payment.payment_id)
    session = FakeSession()
    outbox_repo = FakeOutboxRepository(session, event)
    finalize = FakeFinalizeCommand(None, None)

    monkeypatch.setattr(outbox_worker, "OutboxRepository", lambda _session: outbox_repo)
    monkeypatch.setattr(
        outbox_worker,
        "PaymentRepository",
        lambda _session: FakePaymentRepository(_session, payment=payment, mark_processing_ok=True),
    )
    monkeypatch.setattr(outbox_worker, "FinalizePaymentCommand", lambda _p, _o: finalize)
    monkeypatch.setattr(outbox_worker.outbox_backlog, "record", lambda *_: None)
    monkeypatch.setattr(outbox_worker.outbox_lag_seconds, "record", lambda *_: None)

    worker = _worker(session, FakeProviderCommand(error=RuntimeError("boom")))
    await worker.run_once()

    assert outbox_repo.failed == [(event.event_id, 1)]
    assert len(finalize.fail_calls) == 1
    assert finalize.fail_calls[0][1] == ProviderName.UNKNOWN.value
    assert finalize.fail_calls[0][2] == PaymentFailureReason.UNEXPECTED.value
    assert session.commits == 1
