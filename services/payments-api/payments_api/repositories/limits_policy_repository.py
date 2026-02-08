from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import LimitsPolicyORM, PaymentMethod


class LimitsPolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_rail(self, rail: PaymentMethod) -> LimitsPolicyORM | None:
        stmt = select(LimitsPolicyORM).where(LimitsPolicyORM.rail == rail)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
