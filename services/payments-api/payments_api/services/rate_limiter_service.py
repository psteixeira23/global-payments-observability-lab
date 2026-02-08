from __future__ import annotations

import time

from redis.asyncio import Redis
from redis.exceptions import RedisError

from payments_api.core.errors import RateLimitedError
from shared.constants import rate_limit_key
from shared.contracts import RateLimitDimension


class RateLimiterService:
    def __init__(
        self,
        redis_client: Redis,
        *,
        merchant_limit: int,
        customer_limit: int,
        account_limit: int,
        window_seconds: int,
    ) -> None:
        self._redis = redis_client
        self._merchant_limit = merchant_limit
        self._customer_limit = customer_limit
        self._account_limit = account_limit
        self._window_seconds = window_seconds

    async def enforce(self, merchant_id: str, customer_id: str, account_id: str) -> None:
        now_bucket = int(time.time() / self._window_seconds)
        checks = [
            (RateLimitDimension.MERCHANT, merchant_id, self._merchant_limit),
            (RateLimitDimension.CUSTOMER, customer_id, self._customer_limit),
            (RateLimitDimension.ACCOUNT, account_id, self._account_limit),
        ]
        for dimension, value, limit in checks:
            if not await self._allow(dimension, value, now_bucket, limit):
                raise RateLimitedError(f"Rate limited by {dimension.value}", dimension=dimension)

    async def _allow(
        self, dimension: RateLimitDimension, value: str, bucket: int, limit: int
    ) -> bool:
        key = rate_limit_key(dimension, value, bucket)
        try:
            current = await self._redis.incr(key)
            if current == 1:
                await self._redis.expire(key, self._window_seconds)
            return current <= limit
        except RedisError:
            return True
