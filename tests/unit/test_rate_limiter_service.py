from __future__ import annotations

import pytest
from payments_api.core.errors import RateLimitedError
from payments_api.services.rate_limiter_service import RateLimiterService


class FakeRedis:
    def __init__(self) -> None:
        self._values: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        value = self._values.get(key, 0) + 1
        self._values[key] = value
        return value

    async def expire(self, key: str, ttl: int) -> bool:  # noqa: ARG002
        return True


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_threshold() -> None:
    limiter = RateLimiterService(
        FakeRedis(),
        merchant_limit=1,
        customer_limit=1,
        account_limit=1,
        window_seconds=60,
    )

    await limiter.enforce("merchant-1", "customer-1", "account-1")

    with pytest.raises(RateLimitedError):
        await limiter.enforce("merchant-1", "customer-1", "account-1")
