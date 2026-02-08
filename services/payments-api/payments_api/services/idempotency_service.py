from __future__ import annotations

from redis.asyncio import Redis
from redis.exceptions import RedisError

from shared.logging import get_logger
from shared.utils.ids import idempotency_scoped_key

logger = get_logger(__name__)


class IdempotencyService:
    def __init__(self, redis_client: Redis, ttl_seconds: int) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    async def acquire(self, merchant_id: str, idempotency_key: str) -> bool:
        scoped = idempotency_scoped_key(merchant_id, idempotency_key)
        try:
            acquired = await self._redis.set(scoped, "1", ex=self._ttl_seconds, nx=True)
            return bool(acquired)
        except RedisError as exc:
            logger.warning(
                "idempotency_redis_unavailable",
                extra={
                    "extra_fields": {
                        "error_type": type(exc).__name__,
                        "idempotency_key": idempotency_key,
                    }
                },
            )
            return True
