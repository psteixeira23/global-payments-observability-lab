from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import pytest
from payments_api.core.errors import LimitExceededError
from payments_api.services.limits_service import LimitsService

from shared.contracts import LimitsPolicyORM, PaymentMethod


@dataclass
class FakeLimitsPolicyRepo:
    policy: LimitsPolicyORM

    async def get_by_rail(self, rail: PaymentMethod) -> LimitsPolicyORM | None:  # noqa: ARG002
        return self.policy


class FakePaymentRepo:
    async def sum_outgoing_since(
        self, customer_id: str, rail: PaymentMethod, since: datetime
    ) -> Decimal:  # noqa: ARG002
        return Decimal("0")

    async def count_outgoing_since(
        self, customer_id: str, rail: PaymentMethod, since: datetime
    ) -> int:  # noqa: ARG002
        return 0


class FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._zsets: dict[str, dict[str, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        return self._kv.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:  # noqa: ARG002
        self._kv[key] = value
        return True

    async def zremrangebyscore(
        self, key: str, min_score: float, max_score: float
    ) -> int:  # noqa: ARG002
        async with self._lock:
            zset = self._zsets.setdefault(key, {})
            before = len(zset)
            keys = [k for k, score in zset.items() if min_score <= score <= max_score]
            for item in keys:
                zset.pop(item, None)
            return before - len(zset)

    async def zcard(self, key: str) -> int:
        async with self._lock:
            return len(self._zsets.setdefault(key, {}))

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        async with self._lock:
            zset = self._zsets.setdefault(key, {})
            for member, score in mapping.items():
                zset[member] = score
            return len(mapping)

    async def expire(self, key: str, ttl: int) -> bool:  # noqa: ARG002
        return True


def _policy() -> LimitsPolicyORM:
    return LimitsPolicyORM(
        rail=PaymentMethod.PIX,
        min_amount=Decimal("1.00"),
        max_amount=Decimal("100.00"),
        daily_limit_amount=Decimal("150.00"),
        velocity_limit_count=2,
        velocity_window_seconds=60,
    )


@pytest.mark.asyncio
async def test_daily_limit_exceeded() -> None:
    redis = FakeRedis()
    service = LimitsService(redis, cache_ttl_seconds=60)
    policy = _policy()
    repo = FakePaymentRepo()
    policy_repo = FakeLimitsPolicyRepo(policy)

    await service.enforce(
        repo,
        policy_repo,
        customer_id="customer-1",
        rail=PaymentMethod.PIX,
        amount=Decimal("100.00"),
    )

    with pytest.raises(LimitExceededError):
        await service.enforce(
            repo,
            policy_repo,
            customer_id="customer-1",
            rail=PaymentMethod.PIX,
            amount=Decimal("100.00"),
        )


@pytest.mark.asyncio
async def test_velocity_limit_exceeded_under_concurrency() -> None:
    redis = FakeRedis()
    service = LimitsService(redis, cache_ttl_seconds=60)
    policy_repo = FakeLimitsPolicyRepo(_policy())
    payment_repo = FakePaymentRepo()

    async def call_once() -> str:
        try:
            await service.enforce(
                payment_repo,
                policy_repo,
                customer_id="customer-velocity",
                rail=PaymentMethod.PIX,
                amount=Decimal("10.00"),
            )
            return "ok"
        except LimitExceededError:
            return "limit"

    results = await asyncio.gather(*[call_once() for _ in range(3)])
    assert results.count("limit") >= 1
