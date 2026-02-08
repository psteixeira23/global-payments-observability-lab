from __future__ import annotations

import time
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from payments_api.core.errors import LimitExceededError, ValidationAppError
from shared.constants import limits_daily_key, limits_policy_key, limits_velocity_key
from shared.contracts import LimitsPolicyDTO, LimitsPolicyORM, PaymentMethod


@dataclass
class LimitsEvaluation:
    policy: LimitsPolicyDTO
    velocity_count: int


class LimitsPaymentReadRepository(Protocol):
    def sum_outgoing_since(
        self,
        customer_id: str,
        rail: PaymentMethod,
        since: datetime,
    ) -> Awaitable[Decimal]: ...

    def count_outgoing_since(
        self,
        customer_id: str,
        rail: PaymentMethod,
        since: datetime,
    ) -> Awaitable[int]: ...


class LimitsPolicyReadRepository(Protocol):
    def get_by_rail(self, rail: PaymentMethod) -> Awaitable[LimitsPolicyORM | None]: ...


class LimitsService:
    def __init__(self, redis_client: Redis, cache_ttl_seconds: int) -> None:
        self._redis = redis_client
        self._cache_ttl_seconds = cache_ttl_seconds

    async def enforce(
        self,
        payment_repository: LimitsPaymentReadRepository,
        policy_repository: LimitsPolicyReadRepository,
        *,
        customer_id: str,
        rail: PaymentMethod,
        amount: Decimal,
    ) -> LimitsEvaluation:
        policy = await self._get_policy(policy_repository, rail)
        self._enforce_transaction_amount(policy, amount)
        await self._enforce_daily_limit(payment_repository, customer_id, rail, amount, policy)
        velocity_count = await self._enforce_velocity_limit(
            payment_repository, customer_id, rail, policy
        )
        return LimitsEvaluation(policy=policy, velocity_count=velocity_count)

    async def _get_policy(
        self, repository: LimitsPolicyReadRepository, rail: PaymentMethod
    ) -> LimitsPolicyDTO:
        cache_key = limits_policy_key(rail)
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                return LimitsPolicyDTO.model_validate_json(cached)
        except (RedisError, ValidationError):
            pass

        entity = await repository.get_by_rail(rail)
        if not entity:
            raise ValidationAppError(f"Missing limits policy for rail {rail.value}")

        policy = LimitsPolicyDTO(
            rail=entity.rail,
            min_amount=entity.min_amount,
            max_amount=entity.max_amount,
            daily_limit_amount=entity.daily_limit_amount,
            velocity_limit_count=entity.velocity_limit_count,
            velocity_window_seconds=entity.velocity_window_seconds,
        )
        try:
            await self._redis.set(cache_key, policy.model_dump_json(), ex=self._cache_ttl_seconds)
        except RedisError:
            pass
        return policy

    def _enforce_transaction_amount(self, policy: LimitsPolicyDTO, amount: Decimal) -> None:
        if amount < policy.min_amount:
            raise LimitExceededError(f"Amount below min limit for {policy.rail.value}")
        if amount > policy.max_amount:
            raise LimitExceededError(f"Amount above max limit for {policy.rail.value}")

    async def _enforce_daily_limit(
        self,
        payment_repository: LimitsPaymentReadRepository,
        customer_id: str,
        rail: PaymentMethod,
        amount: Decimal,
        policy: LimitsPolicyDTO,
    ) -> None:
        amount_cents = _as_cents(amount)
        limit_cents = _as_cents(policy.daily_limit_amount)
        date_key = _current_utc().strftime("%Y%m%d")
        redis_key = limits_daily_key(date_key, customer_id, rail)

        try:
            current = await self._redis_get_int(redis_key)
            projected = current + amount_cents
            if projected > limit_cents:
                self._raise_daily_limit_exceeded(rail)
            ttl = _seconds_until_day_end()
            await self._redis.set(redis_key, str(projected), ex=ttl)
            return
        except LimitExceededError:
            raise
        except (RedisError, ValueError):
            pass

        day_start = _utc_day_start()
        total = await payment_repository.sum_outgoing_since(customer_id, rail, day_start)
        if total + amount > policy.daily_limit_amount:
            self._raise_daily_limit_exceeded(rail)

    async def _enforce_velocity_limit(
        self,
        payment_repository: LimitsPaymentReadRepository,
        customer_id: str,
        rail: PaymentMethod,
        policy: LimitsPolicyDTO,
    ) -> int:
        now = time.time()
        window_start = now - policy.velocity_window_seconds
        redis_key = limits_velocity_key(customer_id, rail)

        try:
            await self._redis.zremrangebyscore(redis_key, 0, window_start)
            count = int(await self._redis.zcard(redis_key))
            if count >= policy.velocity_limit_count:
                self._raise_velocity_limit_exceeded(rail)
            member = f"{now}-{count}"
            await self._redis.zadd(redis_key, {member: now})
            await self._redis.expire(redis_key, policy.velocity_window_seconds)
            return count + 1
        except LimitExceededError:
            raise
        except RedisError:
            pass

        since = datetime.fromtimestamp(window_start, tz=UTC)
        count = await payment_repository.count_outgoing_since(customer_id, rail, since)
        if count >= policy.velocity_limit_count:
            self._raise_velocity_limit_exceeded(rail)
        return count + 1

    async def _redis_get_int(self, key: str) -> int:
        raw_value = await self._redis.get(key)
        return int(raw_value or "0")

    def _raise_daily_limit_exceeded(self, rail: PaymentMethod) -> None:
        raise LimitExceededError(f"Daily limit exceeded for rail {rail.value}")

    def _raise_velocity_limit_exceeded(self, rail: PaymentMethod) -> None:
        raise LimitExceededError(f"Velocity limit exceeded for rail {rail.value}")


def _as_cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def _seconds_until_day_end() -> int:
    now = _current_utc()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return max(1, int((end - now).total_seconds()))


def _current_utc() -> datetime:
    return datetime.now(UTC)


def _utc_day_start() -> datetime:
    now = _current_utc()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)
