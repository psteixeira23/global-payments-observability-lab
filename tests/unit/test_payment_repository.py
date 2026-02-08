from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from payments_api.repositories.payment_repository import PaymentCreateData, PaymentRepository

from shared.contracts import AmlDecision, PaymentMethod, PaymentStatus, RiskDecision


class FakeExecuteResult:
    def __init__(
        self,
        *,
        scalar_value: object | None = None,
        scalar_one_or_none_value: object | None = None,
        rowcount: int = 0,
    ) -> None:
        self._scalar_value = scalar_value
        self._scalar_one_or_none_value = scalar_one_or_none_value
        self.rowcount = rowcount

    def scalar_one(self) -> object | None:
        return self._scalar_value

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_one_or_none_value


class FakeSession:
    def __init__(self, results: list[FakeExecuteResult] | None = None) -> None:
        self._results = results or []
        self.executed_statements: list[str] = []
        self.added_entities: list[object] = []

    async def execute(self, statement):  # noqa: ANN001
        self.executed_statements.append(str(statement))
        if not self._results:
            return FakeExecuteResult()
        return self._results.pop(0)

    def add(self, entity: object) -> None:
        self.added_entities.append(entity)


@pytest.mark.asyncio
async def test_destination_seen_short_circuits_when_destination_is_none() -> None:
    session = FakeSession([FakeExecuteResult(scalar_one_or_none_value="unused")])
    repository = PaymentRepository(session)  # type: ignore[arg-type]

    result = await repository.destination_seen("customer-1", None)

    assert result is False
    assert session.executed_statements == []


@pytest.mark.asyncio
async def test_destination_seen_queries_with_limit_and_returns_boolean() -> None:
    session_with_match = FakeSession([FakeExecuteResult(scalar_one_or_none_value="payment-id")])
    repository_with_match = PaymentRepository(session_with_match)  # type: ignore[arg-type]
    exists = await repository_with_match.destination_seen("customer-1", "dest-1")

    session_without_match = FakeSession([FakeExecuteResult(scalar_one_or_none_value=None)])
    repository_without_match = PaymentRepository(session_without_match)  # type: ignore[arg-type]
    missing = await repository_without_match.destination_seen("customer-1", "dest-1")

    assert exists is True
    assert missing is False
    assert "LIMIT" in session_with_match.executed_statements[0]


def test_create_payment_maps_fields_and_adds_entity() -> None:
    session = FakeSession()
    repository = PaymentRepository(session)  # type: ignore[arg-type]
    payment_data = PaymentCreateData(
        payment_id=uuid4(),
        merchant_id="merchant-1",
        customer_id="customer-1",
        account_id="account-1",
        amount=Decimal("120.50"),
        currency="BRL",
        method=PaymentMethod.PIX,
        destination="pix-key-1",
        status=PaymentStatus.RECEIVED,
        idempotency_key="idem-1",
        risk_score=42,
        risk_decision=RiskDecision.REVIEW,
        aml_decision=AmlDecision.ALLOW,
        metadata={"source": "test"},
    )

    entity = repository.create_payment(payment_data)

    assert session.added_entities[0] is entity
    assert entity.payment_id == payment_data.payment_id
    assert entity.merchant_id == "merchant-1"
    assert entity.risk_decision == RiskDecision.REVIEW
    assert entity.metadata_json == {"source": "test"}


@pytest.mark.asyncio
async def test_update_status_returns_true_when_row_is_updated() -> None:
    session = FakeSession([FakeExecuteResult(rowcount=1)])
    repository = PaymentRepository(session)  # type: ignore[arg-type]

    updated = await repository.update_status(uuid4(), PaymentStatus.CONFIRMED, last_error=None)

    assert updated is True
    assert "UPDATE payments" in session.executed_statements[0]


@pytest.mark.asyncio
async def test_count_in_review_returns_integer_from_scalar_result() -> None:
    session = FakeSession([FakeExecuteResult(scalar_value=3)])
    repository = PaymentRepository(session)  # type: ignore[arg-type]

    total = await repository.count_in_review()

    assert total == 3
    assert "payments.status" in session.executed_statements[0]


@pytest.mark.asyncio
async def test_sum_outgoing_since_excludes_blocked_status() -> None:
    session = FakeSession([FakeExecuteResult(scalar_value=Decimal("42.00"))])
    repository = PaymentRepository(session)  # type: ignore[arg-type]

    total = await repository.sum_outgoing_since(
        customer_id="customer-1",
        rail=PaymentMethod.PIX,
        since=datetime.now(UTC),
    )

    assert total == Decimal("42.00")
    assert "payments.status !=" in session.executed_statements[0]
