from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import AmlDecision, PaymentMethod, PaymentORM, PaymentStatus, RiskDecision


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_payment_id(self, payment_id: UUID) -> PaymentORM | None:
        stmt = select(PaymentORM).where(PaymentORM.payment_id == payment_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_merchant_and_idempotency(
        self, merchant_id: str, idempotency_key: str
    ) -> PaymentORM | None:
        stmt = select(PaymentORM).where(
            PaymentORM.merchant_id == merchant_id,
            PaymentORM.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_payment(
        self,
        *,
        payment_id: UUID,
        merchant_id: str,
        customer_id: str,
        account_id: str,
        amount: Decimal,
        currency: str,
        method: PaymentMethod,
        destination: str | None,
        status: PaymentStatus,
        idempotency_key: str,
        risk_score: int,
        risk_decision: RiskDecision,
        aml_decision: AmlDecision,
        metadata: dict | None,
    ) -> PaymentORM:
        entity = PaymentORM(
            payment_id=payment_id,
            merchant_id=merchant_id,
            customer_id=customer_id,
            account_id=account_id,
            amount=amount,
            currency=currency,
            method=method,
            destination=destination,
            status=status,
            idempotency_key=idempotency_key,
            risk_score=risk_score,
            risk_decision=risk_decision,
            aml_decision=aml_decision,
            metadata_json=metadata,
        )
        self._session.add(entity)
        return entity

    async def update_status(
        self, payment_id: UUID, status: PaymentStatus, *, last_error: str | None = None
    ) -> bool:
        stmt = (
            update(PaymentORM)
            .where(PaymentORM.payment_id == payment_id)
            .values(status=status, last_error=last_error)
        )
        result = await self._session.execute(stmt)
        return bool(getattr(result, "rowcount", 0))

    async def sum_outgoing_since(
        self,
        customer_id: str,
        rail: PaymentMethod,
        since: datetime,
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(PaymentORM.amount), 0)).where(
            PaymentORM.customer_id == customer_id,
            PaymentORM.method == rail,
            PaymentORM.created_at >= since,
            PaymentORM.status != PaymentStatus.BLOCKED,
        )
        result = await self._session.execute(stmt)
        return Decimal(result.scalar_one())

    async def count_outgoing_since(
        self, customer_id: str, rail: PaymentMethod, since: datetime
    ) -> int:
        stmt = select(func.count()).where(
            PaymentORM.customer_id == customer_id,
            PaymentORM.method == rail,
            PaymentORM.created_at >= since,
            PaymentORM.status != PaymentStatus.BLOCKED,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_failures_since(self, customer_id: str, since: datetime) -> int:
        stmt = select(func.count()).where(
            PaymentORM.customer_id == customer_id,
            PaymentORM.status == PaymentStatus.FAILED,
            PaymentORM.created_at >= since,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def destination_seen(self, customer_id: str, destination: str | None) -> bool:
        if not destination:
            return False
        stmt = select(PaymentORM.payment_id).where(
            PaymentORM.customer_id == customer_id,
            PaymentORM.destination == destination,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count_near_threshold_since(
        self,
        customer_id: str,
        rail: PaymentMethod,
        since: datetime,
        low_amount: Decimal,
        high_amount: Decimal,
    ) -> int:
        stmt = select(func.count()).where(
            PaymentORM.customer_id == customer_id,
            PaymentORM.method == rail,
            PaymentORM.created_at >= since,
            and_(PaymentORM.amount >= low_amount, PaymentORM.amount <= high_amount),
            PaymentORM.status != PaymentStatus.BLOCKED,
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_in_review(self) -> int:
        stmt = select(func.count()).where(PaymentORM.status == PaymentStatus.IN_REVIEW)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
