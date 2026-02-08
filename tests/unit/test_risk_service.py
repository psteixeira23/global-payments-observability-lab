from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from payments_api.services.risk_service import RiskScoreService

from shared.contracts import (
    CustomerORM,
    CustomerStatus,
    KycLevel,
    LimitsPolicyDTO,
    PaymentMethod,
    RiskDecision,
)


class FakePaymentRepo:
    def __init__(self, failures: int, destination_seen: bool) -> None:
        self._failures = failures
        self._destination_seen = destination_seen

    async def count_failures_since(self, customer_id: str, since: datetime) -> int:  # noqa: ARG002
        await asyncio.sleep(0)
        return self._failures

    async def destination_seen(self, customer_id: str, destination: str | None) -> bool:  # noqa: ARG002
        await asyncio.sleep(0)
        return self._destination_seen


def _customer(kyc_level: KycLevel, created_at: datetime) -> CustomerORM:
    return CustomerORM(
        customer_id="customer-risk",
        kyc_level=kyc_level,
        status=CustomerStatus.ACTIVE,
        created_at=created_at,
    )


def _policy() -> LimitsPolicyDTO:
    return LimitsPolicyDTO(
        rail=PaymentMethod.PIX,
        min_amount=Decimal("1.00"),
        max_amount=Decimal("100.00"),
        daily_limit_amount=Decimal("1000.00"),
        velocity_limit_count=5,
        velocity_window_seconds=60,
    )


@pytest.mark.asyncio
async def test_risk_engine_returns_block_for_high_risk_context() -> None:
    service = RiskScoreService(review_threshold=50, block_threshold=80)
    repository = FakePaymentRepo(failures=5, destination_seen=False)

    score, decision = await service.evaluate(
        repository,
        customer=_customer(KycLevel.BASIC, datetime.now(UTC)),
        amount=Decimal("95.00"),
        policy=_policy(),
        velocity_count=5,
        destination="dest-new-1",
    )

    assert score >= 80
    assert decision == RiskDecision.BLOCK


@pytest.mark.asyncio
async def test_risk_engine_returns_allow_for_low_risk_context() -> None:
    service = RiskScoreService(review_threshold=50, block_threshold=80)
    repository = FakePaymentRepo(failures=0, destination_seen=True)

    score, decision = await service.evaluate(
        repository,
        customer=_customer(KycLevel.FULL, datetime(2020, 1, 1, tzinfo=UTC)),
        amount=Decimal("10.00"),
        policy=_policy(),
        velocity_count=1,
        destination="dest-known-1",
    )

    assert score < 50
    assert decision == RiskDecision.ALLOW
