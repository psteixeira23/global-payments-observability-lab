from __future__ import annotations

import time
from decimal import Decimal

import pytest
from payments_api.services.aml_service import AmlRuleEngine

from shared.contracts import AmlDecision, LimitsPolicyDTO, PaymentMethod


class FakeRedis:
    def __init__(self, entries: list[str]) -> None:
        self._entries = entries

    async def lrange(self, key: str, start: int, end: int):  # noqa: ARG002
        return self._entries

    async def lpush(self, key: str, payload: str):  # noqa: ARG002
        self._entries.insert(0, payload)
        return len(self._entries)

    async def ltrim(self, key: str, start: int, end: int):  # noqa: ARG002
        self._entries = self._entries[start : end + 1]
        return True

    async def expire(self, key: str, ttl: int):  # noqa: ARG002
        return True


class FakePaymentRepo:
    async def sum_outgoing_since(
        self, customer_id: str, rail: PaymentMethod, since
    ):  # noqa: ANN001, ARG002
        return Decimal("0")

    async def count_near_threshold_since(
        self, customer_id: str, rail: PaymentMethod, since, low_amount, high_amount
    ):  # noqa: ANN001, ARG002
        return 0


def _policy() -> LimitsPolicyDTO:
    return LimitsPolicyDTO(
        rail=PaymentMethod.PIX,
        min_amount=Decimal("1.00"),
        max_amount=Decimal("100.00"),
        daily_limit_amount=Decimal("1000.00"),
        velocity_limit_count=10,
        velocity_window_seconds=60,
    )


@pytest.mark.asyncio
async def test_aml_blocks_high_risk_destination() -> None:
    engine = AmlRuleEngine(
        FakeRedis([]),
        blocklist_destinations={"dest-blocked-001"},
        total_window_seconds=600,
        total_threshold_amount=Decimal("5000.00"),
        structuring_window_seconds=900,
        structuring_count_threshold=3,
    )

    decision = await engine.evaluate(
        FakePaymentRepo(),
        customer_id="customer-1",
        rail=PaymentMethod.PIX,
        amount=Decimal("10.00"),
        destination="dest-blocked-001",
        policy=_policy(),
    )

    assert decision == AmlDecision.BLOCK


@pytest.mark.asyncio
async def test_aml_structuring_detection_returns_review() -> None:
    now = int(time.time())
    entries = [
        f"{now}|PIX|96.00",
        f"{now}|PIX|97.00",
    ]
    engine = AmlRuleEngine(
        FakeRedis(entries),
        blocklist_destinations=set(),
        total_window_seconds=600,
        total_threshold_amount=Decimal("5000.00"),
        structuring_window_seconds=900,
        structuring_count_threshold=3,
    )

    decision = await engine.evaluate(
        FakePaymentRepo(),
        customer_id="customer-1",
        rail=PaymentMethod.PIX,
        amount=Decimal("98.00"),
        destination="dest-safe-1",
        policy=_policy(),
    )

    assert decision == AmlDecision.REVIEW
