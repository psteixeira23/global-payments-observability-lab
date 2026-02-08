from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from payments_processor.repositories.outbox_repository import OutboxRepository
from payments_processor.repositories.payment_repository import PaymentRepository

from shared.contracts import EventType, OutboxStatus


class FakeScalarsResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class FakeExecuteResult:
    def __init__(
        self,
        *,
        scalar_one_value: object | None = None,
        scalar_one_or_none_value: object | None = None,
        scalars_values: list[object] | None = None,
        rowcount: int = 0,
    ) -> None:
        self._scalar_one_value = scalar_one_value
        self._scalar_one_or_none_value = scalar_one_or_none_value
        self._scalars_values = scalars_values or []
        self.rowcount = rowcount

    def scalar_one(self) -> object | None:
        return self._scalar_one_value

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_one_or_none_value

    def scalars(self) -> FakeScalarsResult:
        return FakeScalarsResult(self._scalars_values)


class FakeSession:
    def __init__(self, results: list[FakeExecuteResult] | None = None) -> None:
        self._results = results or []
        self.executed_statements: list[str] = []
        self.added_entities: list[object] = []

    async def execute(self, stmt):  # noqa: ANN001
        self.executed_statements.append(str(stmt))
        if self._results:
            return self._results.pop(0)
        return FakeExecuteResult()

    def add(self, entity: object) -> None:
        self.added_entities.append(entity)


@pytest.mark.asyncio
async def test_processor_payment_repository_transitions_and_optimistic_locking() -> None:
    payment_id = uuid4()
    payment = SimpleNamespace(payment_id=payment_id, version=3)
    session = FakeSession(
        [
            FakeExecuteResult(scalar_one_or_none_value=payment),
            FakeExecuteResult(rowcount=1),
            FakeExecuteResult(rowcount=1),
            FakeExecuteResult(rowcount=1),
        ]
    )
    repository = PaymentRepository(session)  # type: ignore[arg-type]

    loaded = await repository.get_by_id(payment_id)
    processing = await repository.mark_processing(payment)
    confirmed = await repository.mark_confirmed(payment)
    failed = await repository.mark_failed(payment, "provider failure")

    assert loaded is payment
    assert processing is True
    assert confirmed is True
    assert failed is True
    assert "version = :version_1" in session.executed_statements[1]
    assert "SET status=:status" in session.executed_statements[1]
    assert "SET status=:status" in session.executed_statements[2]
    assert "last_error=:last_error" in session.executed_statements[3]


@pytest.mark.asyncio
async def test_processor_outbox_repository_fetches_and_marks_events() -> None:
    event_id = uuid4()
    event = SimpleNamespace(event_id=event_id, created_at=datetime.now(UTC) - timedelta(seconds=10))
    session = FakeSession(
        [
            FakeExecuteResult(scalars_values=[event]),
            FakeExecuteResult(),
            FakeExecuteResult(),
            FakeExecuteResult(),
            FakeExecuteResult(scalar_one_value=4),
            FakeExecuteResult(scalar_one_or_none_value=event.created_at),
            FakeExecuteResult(scalar_one_or_none_value=None),
        ]
    )
    repository = OutboxRepository(session)  # type: ignore[arg-type]

    fetched = await repository.fetch_pending_requested(limit=20)
    await repository.mark_sent(event_id)
    await repository.mark_failed(event_id, attempts=2)
    await repository.reschedule(event_id, attempts=3, delay_seconds=1.5)
    backlog = await repository.backlog_size()
    lag = await repository.oldest_pending_lag_seconds()
    empty_lag = await repository.oldest_pending_lag_seconds()

    assert fetched == [event]
    assert backlog == 4
    assert lag >= 0
    assert empty_lag == 0.0
    assert "outbox_events.event_type = :event_type_1" in session.executed_statements[0]
    assert "SET status=:status" in session.executed_statements[1]
    assert "SET status=:status" in session.executed_statements[2]


def test_processor_outbox_repository_emit_event_adds_pending_entity() -> None:
    session = FakeSession()
    repository = OutboxRepository(session)  # type: ignore[arg-type]
    aggregate_id = uuid4()

    repository.emit_event(
        aggregate_id=aggregate_id,
        event_type=EventType.PAYMENT_FAILED,
        payload={"reason": "provider_5xx"},
    )

    event = session.added_entities[0]
    assert event.aggregate_id == aggregate_id
    assert event.event_type == EventType.PAYMENT_FAILED
    assert event.status == OutboxStatus.PENDING
