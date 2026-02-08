from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol

from shared.contracts import CustomerORM, KycLevel, LimitsPolicyDTO, RiskDecision


@dataclass(frozen=True)
class RiskContext:
    amount: Decimal
    policy_max: Decimal
    velocity_count: int
    velocity_limit: int
    repeated_failures: int
    is_new_customer: bool
    customer_kyc: KycLevel
    destination_seen: bool


class RiskRule(Protocol):
    def score(self, context: RiskContext) -> int: ...


class RiskReadRepository(Protocol):
    def count_failures_since(self, customer_id: str, since: datetime) -> Awaitable[int]: ...

    def destination_seen(
        self, customer_id: str, destination: str | None
    ) -> Awaitable[bool]: ...


class AmountNearMaxRule:
    def score(self, context: RiskContext) -> int:
        threshold = context.policy_max * Decimal("0.9")
        return 25 if context.amount >= threshold else 0


class VelocitySpikeRule:
    def score(self, context: RiskContext) -> int:
        if context.velocity_limit <= 0:
            return 0
        ratio = context.velocity_count / context.velocity_limit
        if ratio >= 0.8:
            return 20
        return 0


class RepeatedFailuresRule:
    def score(self, context: RiskContext) -> int:
        if context.repeated_failures >= 3:
            return 25
        if context.repeated_failures >= 1:
            return 10
        return 0


class NewCustomerLowKycRule:
    def score(self, context: RiskContext) -> int:
        if context.is_new_customer and context.customer_kyc in {KycLevel.NONE, KycLevel.BASIC}:
            return 20
        return 0


class NewDestinationRule:
    def score(self, context: RiskContext) -> int:
        return 15 if not context.destination_seen else 0


class RiskScoreService:
    def __init__(self, review_threshold: int, block_threshold: int) -> None:
        self._review_threshold = review_threshold
        self._block_threshold = block_threshold
        self._rules: list[RiskRule] = [
            AmountNearMaxRule(),
            VelocitySpikeRule(),
            RepeatedFailuresRule(),
            NewCustomerLowKycRule(),
            NewDestinationRule(),
        ]

    async def evaluate(
        self,
        payment_repository: RiskReadRepository,
        *,
        customer: CustomerORM,
        amount: Decimal,
        policy: LimitsPolicyDTO,
        velocity_count: int,
        destination: str | None,
    ) -> tuple[int, RiskDecision]:
        now = datetime.now(UTC)
        repeated_failures = await payment_repository.count_failures_since(
            customer.customer_id, now - timedelta(days=1)
        )
        destination_seen = await payment_repository.destination_seen(
            customer.customer_id, destination
        )

        context = RiskContext(
            amount=amount,
            policy_max=policy.max_amount,
            velocity_count=velocity_count,
            velocity_limit=policy.velocity_limit_count,
            repeated_failures=repeated_failures,
            is_new_customer=self._is_new_customer(customer, now),
            customer_kyc=customer.kyc_level,
            destination_seen=destination_seen,
        )
        score = min(100, sum(rule.score(context) for rule in self._rules))
        return score, self._decision_from_score(score)

    def _is_new_customer(self, customer: CustomerORM, now: datetime) -> bool:
        created_at = getattr(customer, "created_at", None)
        if created_at is None:
            return True
        return (now - created_at) < timedelta(days=7)

    def _decision_from_score(self, score: int) -> RiskDecision:
        if score >= self._block_threshold:
            return RiskDecision.BLOCK
        if score >= self._review_threshold:
            return RiskDecision.REVIEW
        return RiskDecision.ALLOW
