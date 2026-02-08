from __future__ import annotations

from uuid import uuid4

import pytest
from payments_api.repositories.customer_repository import CustomerRepository
from payments_api.repositories.idempotency_repository import IdempotencyRepository
from payments_api.repositories.limits_policy_repository import LimitsPolicyRepository
from payments_api.repositories.outbox_repository import OutboxRepository

from shared.contracts import EventType, PaymentMethod


class FakeExecuteResult:
    def __init__(self, value) -> None:  # noqa: ANN001
        self._value = value

    def scalar_one_or_none(self):  # noqa: ANN201
        return self._value


class FakeSession:
    def __init__(self, result_value=None) -> None:  # noqa: ANN001
        self._result_value = result_value
        self.executed_statements: list[str] = []
        self.added_entities: list[object] = []

    async def execute(self, stmt):  # noqa: ANN001
        self.executed_statements.append(str(stmt))
        return FakeExecuteResult(self._result_value)

    def add(self, entity: object) -> None:
        self.added_entities.append(entity)


@pytest.mark.asyncio
async def test_customer_repository_get_by_id_queries_customer_table() -> None:
    session = FakeSession(result_value="customer")
    repository = CustomerRepository(session)  # type: ignore[arg-type]

    customer = await repository.get_by_id("customer-1")

    assert customer == "customer"
    assert "FROM customers" in session.executed_statements[0]


@pytest.mark.asyncio
async def test_limits_policy_repository_get_by_rail_queries_limits_table() -> None:
    session = FakeSession(result_value="policy")
    repository = LimitsPolicyRepository(session)  # type: ignore[arg-type]

    policy = await repository.get_by_rail(PaymentMethod.PIX)

    assert policy == "policy"
    assert "FROM limits_policies" in session.executed_statements[0]


@pytest.mark.asyncio
async def test_idempotency_repository_get_snapshot_by_scope() -> None:
    session = FakeSession(result_value="snapshot")
    repository = IdempotencyRepository(session)  # type: ignore[arg-type]

    snapshot = await repository.get_snapshot("merchant-1", "idem-1")

    assert snapshot == "snapshot"
    assert "FROM idempotency_records" in session.executed_statements[0]


def test_idempotency_repository_create_snapshot_persists_record() -> None:
    session = FakeSession()
    repository = IdempotencyRepository(session)  # type: ignore[arg-type]
    payment_id = uuid4()

    record = repository.create_snapshot(
        merchant_id="merchant-1",
        idempotency_key="idem-1",
        payment_id=payment_id,
        status_code=202,
        response_payload={"status": "RECEIVED"},
    )

    assert session.added_entities[0] is record
    assert record.payment_id == payment_id
    assert record.status_code == 202


def test_outbox_repository_add_event_creates_pending_event() -> None:
    session = FakeSession()
    repository = OutboxRepository(session)  # type: ignore[arg-type]
    aggregate_id = uuid4()

    event = repository.add_event(
        aggregate_id=aggregate_id,
        event_type=EventType.PAYMENT_REQUESTED,
        payload={"trace_id": "trace-1"},
    )

    assert session.added_entities[0] is event
    assert event.aggregate_id == aggregate_id
    assert event.event_type == EventType.PAYMENT_REQUESTED
    assert event.payload == {"trace_id": "trace-1"}
