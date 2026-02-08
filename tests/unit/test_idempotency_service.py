from __future__ import annotations

import asyncio

import pytest
from payments_api.services.idempotency_service import IdempotencyService
from redis.exceptions import RedisError


class FakeRedis:
    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail
        self._seen: set[str] = set()

    async def set(self, key: str, value: str, ex: int, nx: bool) -> bool:  # noqa: ARG002
        await asyncio.sleep(0)
        if self._should_fail:
            raise RedisError("redis down")
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


@pytest.mark.asyncio
async def test_acquire_returns_true_then_false_for_same_key() -> None:
    service = IdempotencyService(FakeRedis(), ttl_seconds=60)

    first = await service.acquire("merchant-1", "idem-1")
    second = await service.acquire("merchant-1", "idem-1")

    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_acquire_falls_back_to_true_when_redis_unavailable() -> None:
    service = IdempotencyService(FakeRedis(should_fail=True), ttl_seconds=60)

    acquired = await service.acquire("merchant-1", "idem-1")

    assert acquired is True
