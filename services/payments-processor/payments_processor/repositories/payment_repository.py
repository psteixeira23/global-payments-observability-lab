from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import PaymentORM, PaymentStatus


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, payment_id: UUID) -> PaymentORM | None:
        stmt = select(PaymentORM).where(PaymentORM.payment_id == payment_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_processing(self, payment: PaymentORM) -> bool:
        stmt = (
            update(PaymentORM)
            .where(
                PaymentORM.payment_id == payment.payment_id, PaymentORM.version == payment.version
            )
            .values(status=PaymentStatus.PROCESSING, version=payment.version + 1)
        )
        result = await self._session.execute(stmt)
        return bool(getattr(result, "rowcount", 0))

    async def mark_confirmed(self, payment: PaymentORM) -> bool:
        stmt = (
            update(PaymentORM)
            .where(PaymentORM.payment_id == payment.payment_id)
            .values(status=PaymentStatus.CONFIRMED, version=payment.version + 2, last_error=None)
        )
        result = await self._session.execute(stmt)
        return bool(getattr(result, "rowcount", 0))

    async def mark_failed(self, payment: PaymentORM, reason: str) -> bool:
        stmt = (
            update(PaymentORM)
            .where(PaymentORM.payment_id == payment.payment_id)
            .values(status=PaymentStatus.FAILED, version=payment.version + 2, last_error=reason)
        )
        result = await self._session.execute(stmt)
        return bool(getattr(result, "rowcount", 0))
