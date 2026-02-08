from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from payments_api.core.config import Settings
from payments_api.services.idempotency_service import IdempotencyService
from payments_api.use_cases import create_payment as create_payment_module

from shared.contracts import (
    AmlDecision,
    CreatePaymentRequest,
    CustomerStatus,
    KycLevel,
    LimitsPolicyDTO,
    PaymentMethod,
    PaymentStatus,
    RiskDecision,
)


class FakeRedisIdempotency:
    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: str, ex: int, nx: bool) -> bool:  # noqa: ARG002
        async with self._lock:
            if key in self._seen:
                return False
            self._seen.add(key)
            return True


@dataclass
class SnapshotRecord:
    response_payload: dict


class FakeIdempotencyRepository:
    def __init__(self) -> None:
        self.snapshot: SnapshotRecord | None = None

    async def get_snapshot(self, merchant_id: str, idempotency_key: str):  # noqa: ARG002
        return self.snapshot

    async def create_snapshot(self, **kwargs):  # noqa: ANN003
        self.snapshot = SnapshotRecord(response_payload=kwargs["response_payload"])
        return self.snapshot


class FakePaymentRepository:
    def __init__(self) -> None:
        self.payment_id: UUID | None = None
        self.status = PaymentStatus.RECEIVED

    async def get_by_merchant_and_idempotency(
        self, merchant_id: str, idempotency_key: str
    ):  # noqa: ARG002
        if not self.payment_id:
            return None
        return SimpleNamespace(
            payment_id=self.payment_id,
            status=self.status,
            risk_decision=RiskDecision.ALLOW,
            aml_decision=AmlDecision.ALLOW,
        )

    async def create_payment(self, **kwargs):  # noqa: ANN003
        self.payment_id = kwargs["payment_id"]
        return kwargs

    async def count_in_review(self) -> int:
        return 0

    async def count_failures_since(self, customer_id: str, since):  # noqa: ANN001, ARG002
        return 0

    async def destination_seen(self, customer_id: str, destination):  # noqa: ANN001, ARG002
        return True

    async def sum_outgoing_since(
        self, customer_id: str, rail: PaymentMethod, since
    ):  # noqa: ANN001, ARG002
        return Decimal("0")

    async def count_outgoing_since(
        self, customer_id: str, rail: PaymentMethod, since
    ):  # noqa: ANN001, ARG002
        return 0


class FakeOutboxRepository:
    async def add_event(self, **kwargs):  # noqa: ANN003
        return kwargs


class FakeCustomerRepository:
    async def get_by_id(self, customer_id: str):  # noqa: ARG002
        return SimpleNamespace(
            customer_id="customer-1",
            kyc_level=KycLevel.BASIC,
            status=CustomerStatus.ACTIVE,
            created_at=datetime.now(UTC),
        )


class FakeLimitsRepository:
    pass


class FakeSessionFactory:
    class _Session:
        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._Session()

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False


class FakeRateLimiter:
    async def enforce(
        self, merchant_id: str, customer_id: str, account_id: str
    ) -> None:  # noqa: ARG002
        return None


class FakeLimitsService:
    async def enforce(
        self,
        payment_repository,
        limits_repository,
        *,
        customer_id: str,
        rail: PaymentMethod,
        amount: Decimal,
    ):  # noqa: ANN001, ARG002
        return SimpleNamespace(
            policy=LimitsPolicyDTO(
                rail=rail,
                min_amount=Decimal("1.00"),
                max_amount=Decimal("1000.00"),
                daily_limit_amount=Decimal("5000.00"),
                velocity_limit_count=10,
                velocity_window_seconds=60,
            ),
            velocity_count=1,
        )


class FakeRiskService:
    async def evaluate(
        self, payment_repository, *, customer, amount, policy, velocity_count, destination
    ):  # noqa: ANN001, ARG002
        return 10, RiskDecision.ALLOW


class FakeAmlEngine:
    async def evaluate(
        self, payment_repository, *, customer_id, rail, amount, destination, policy
    ):  # noqa: ANN001, ARG002
        return AmlDecision.ALLOW

    async def record_outgoing(
        self, customer_id: str, rail: PaymentMethod, amount: Decimal
    ) -> None:  # noqa: ARG002
        return None


@pytest.mark.asyncio
async def test_concurrent_create_payment_same_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = SimpleNamespace(
        payment=FakePaymentRepository(),
        outbox=FakeOutboxRepository(),
        customer=FakeCustomerRepository(),
        limits=FakeLimitsRepository(),
        idempotency=FakeIdempotencyRepository(),
    )

    use_case = create_payment_module.CreatePaymentUseCase(
        session_factory=FakeSessionFactory(),
        idempotency_service=IdempotencyService(FakeRedisIdempotency(), ttl_seconds=60),
        rate_limiter=FakeRateLimiter(),
        limits_service=FakeLimitsService(),
        risk_service=FakeRiskService(),
        aml_engine=FakeAmlEngine(),
        settings=Settings(),
    )
    monkeypatch.setattr(use_case, "_build_repositories", lambda _session: repositories)

    headers = {
        "X-Merchant-Id": "merchant-1",
        "X-Customer-Id": "customer-1",
        "X-Account-Id": "account-1",
        "Idempotency-Key": "same-key",
    }

    async def fire_once():
        request = CreatePaymentRequest(
            amount=Decimal("100.00"), currency="BRL", method=PaymentMethod.PIX
        )
        return await use_case.execute(request, headers)

    results = await asyncio.gather(*[fire_once() for _ in range(8)])
    unique_ids = {item.payment_id for item in results}

    assert len(unique_ids) == 1
    assert len({item.status for item in results}) == 1
