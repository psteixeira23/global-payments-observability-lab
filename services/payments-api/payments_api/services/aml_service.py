from __future__ import annotations

import time
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Protocol, TypeVar

from redis.asyncio import Redis
from redis.exceptions import RedisError

from shared.constants import AML_HISTORY_MAX_ITEMS, aml_history_key
from shared.contracts import AmlDecision, LimitsPolicyDTO, PaymentMethod

RedisResult = TypeVar("RedisResult")


class AmlReadRepository(Protocol):
    def sum_outgoing_since(
        self,
        customer_id: str,
        rail: PaymentMethod,
        since: datetime,
    ) -> Awaitable[Decimal]: ...

    def count_near_threshold_since(
        self,
        customer_id: str,
        rail: PaymentMethod,
        since: datetime,
        low_amount: Decimal,
        high_amount: Decimal,
    ) -> Awaitable[int]: ...


class AmlRuleEngine:
    def __init__(
        self,
        redis_client: Redis,
        *,
        blocklist_destinations: set[str],
        total_window_seconds: int,
        total_threshold_amount: Decimal,
        structuring_window_seconds: int,
        structuring_count_threshold: int,
    ) -> None:
        self._redis = redis_client
        self._blocklist_destinations = blocklist_destinations
        self._total_window_seconds = total_window_seconds
        self._total_threshold_amount = total_threshold_amount
        self._structuring_window_seconds = structuring_window_seconds
        self._structuring_count_threshold = structuring_count_threshold

    async def evaluate(
        self,
        payment_repository: AmlReadRepository,
        *,
        customer_id: str,
        rail: PaymentMethod,
        amount: Decimal,
        destination: str | None,
        policy: LimitsPolicyDTO,
    ) -> AmlDecision:
        if destination and destination in self._blocklist_destinations:
            return AmlDecision.BLOCK

        total_outgoing = await self._total_outgoing_recent(payment_repository, customer_id, rail)
        if total_outgoing + amount > self._total_threshold_amount:
            return AmlDecision.REVIEW

        near_count = await self._near_threshold_count(
            payment_repository, customer_id, rail, policy.max_amount
        )
        if amount >= policy.max_amount * Decimal("0.95"):
            near_count += 1
        if near_count >= self._structuring_count_threshold:
            return AmlDecision.REVIEW

        return AmlDecision.ALLOW

    async def record_outgoing(self, customer_id: str, rail: PaymentMethod, amount: Decimal) -> None:
        now = time.time()
        payload = f"{int(now)}|{rail.value}|{amount}"
        key = aml_history_key(customer_id)
        try:
            await self._await_redis(self._redis.lpush(key, payload))
            await self._await_redis(self._redis.ltrim(key, 0, AML_HISTORY_MAX_ITEMS))
            await self._await_redis(
                self._redis.expire(
                    key, max(self._total_window_seconds, self._structuring_window_seconds)
                )
            )
        except RedisError:
            return

    async def _total_outgoing_recent(
        self,
        payment_repository: AmlReadRepository,
        customer_id: str,
        rail: PaymentMethod,
    ) -> Decimal:
        key = aml_history_key(customer_id)
        now = int(time.time())
        entries = await self._read_history_entries(key)
        if entries is not None:
            return self._sum_recent(entries, rail.value, now - self._total_window_seconds)

        since = datetime.now(UTC) - timedelta(seconds=self._total_window_seconds)
        return await payment_repository.sum_outgoing_since(customer_id, rail, since)

    async def _near_threshold_count(
        self,
        payment_repository: AmlReadRepository,
        customer_id: str,
        rail: PaymentMethod,
        max_amount: Decimal,
    ) -> int:
        key = aml_history_key(customer_id)
        cutoff = int(time.time()) - self._structuring_window_seconds
        low_amount = max_amount * Decimal("0.95")
        entries = await self._read_history_entries(key)
        if entries is not None:
            return self._count_near(entries, rail.value, cutoff, low_amount, max_amount)

        since = datetime.now(UTC) - timedelta(seconds=self._structuring_window_seconds)
        return await payment_repository.count_near_threshold_since(
            customer_id, rail, since, low_amount, max_amount
        )

    async def _read_history_entries(self, redis_key: str) -> list[str] | None:
        try:
            entries = await self._await_redis(
                self._redis.lrange(redis_key, 0, AML_HISTORY_MAX_ITEMS)
            )
            return [str(entry) for entry in entries]
        except RedisError:
            return None

    async def _await_redis(self, operation: Awaitable[RedisResult] | RedisResult) -> RedisResult:
        if isinstance(operation, Awaitable):
            return await operation
        return operation

    def _sum_recent(self, entries: list[str], rail: str, cutoff_timestamp: int) -> Decimal:
        total = Decimal("0")
        for entry in entries:
            parsed = self._try_parse_entry(entry)
            if not parsed:
                continue
            ts, current_rail, amount = parsed
            if ts >= cutoff_timestamp and current_rail == rail:
                total += amount
        return total

    def _count_near(
        self,
        entries: list[str],
        rail: str,
        cutoff_timestamp: int,
        low_amount: Decimal,
        max_amount: Decimal,
    ) -> int:
        count = 0
        for entry in entries:
            parsed = self._try_parse_entry(entry)
            if not parsed:
                continue
            ts, current_rail, amount = parsed
            if ts < cutoff_timestamp or current_rail != rail:
                continue
            if low_amount <= amount <= max_amount:
                count += 1
        return count

    def _try_parse_entry(self, entry: str) -> tuple[int, str, Decimal] | None:
        try:
            ts_str, rail, amount_str = entry.split("|", 2)
            return int(ts_str), rail, Decimal(amount_str)
        except (AttributeError, InvalidOperation, ValueError):
            return None
