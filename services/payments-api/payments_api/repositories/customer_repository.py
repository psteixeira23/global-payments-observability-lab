from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import CustomerORM


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, customer_id: str) -> CustomerORM | None:
        stmt = select(CustomerORM).where(CustomerORM.customer_id == customer_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
