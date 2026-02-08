from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import IdempotencyRecordORM


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_snapshot(
        self, merchant_id: str, idempotency_key: str
    ) -> IdempotencyRecordORM | None:
        stmt = select(IdempotencyRecordORM).where(
            IdempotencyRecordORM.merchant_id == merchant_id,
            IdempotencyRecordORM.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def create_snapshot(
        self,
        *,
        merchant_id: str,
        idempotency_key: str,
        payment_id: UUID,
        status_code: int,
        response_payload: dict,
    ) -> IdempotencyRecordORM:
        record = IdempotencyRecordORM(
            merchant_id=merchant_id,
            idempotency_key=idempotency_key,
            payment_id=payment_id,
            status_code=status_code,
            response_payload=response_payload,
        )
        self._session.add(record)
        return record
