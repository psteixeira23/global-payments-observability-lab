from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import EventType, OutboxEventORM, OutboxStatus


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_pending_requested(self, limit: int) -> list[OutboxEventORM]:
        now = datetime.now(UTC)
        stmt = (
            select(OutboxEventORM)
            .where(
                OutboxEventORM.event_type == EventType.PAYMENT_REQUESTED,
                OutboxEventORM.status == OutboxStatus.PENDING,
                OutboxEventORM.next_attempt_at <= now,
            )
            .order_by(OutboxEventORM.created_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_sent(self, event_id: UUID) -> None:
        stmt = (
            update(OutboxEventORM)
            .where(OutboxEventORM.event_id == event_id)
            .values(status=OutboxStatus.SENT)
        )
        await self._session.execute(stmt)

    async def mark_failed(self, event_id: UUID, attempts: int) -> None:
        stmt = (
            update(OutboxEventORM)
            .where(OutboxEventORM.event_id == event_id)
            .values(status=OutboxStatus.FAILED, attempts=attempts)
        )
        await self._session.execute(stmt)

    async def reschedule(self, event_id: UUID, attempts: int, delay_seconds: float) -> None:
        next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        stmt = (
            update(OutboxEventORM)
            .where(OutboxEventORM.event_id == event_id)
            .values(attempts=attempts, next_attempt_at=next_attempt_at)
        )
        await self._session.execute(stmt)

    def emit_event(self, aggregate_id: UUID, event_type: EventType, payload: dict) -> None:
        event = OutboxEventORM(
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            status=OutboxStatus.PENDING,
        )
        self._session.add(event)

    async def backlog_size(self) -> int:
        stmt = (
            select(func.count())
            .select_from(OutboxEventORM)
            .where(
                OutboxEventORM.status == OutboxStatus.PENDING,
                OutboxEventORM.event_type == EventType.PAYMENT_REQUESTED,
            )
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def oldest_pending_lag_seconds(self) -> float:
        stmt = select(func.min(OutboxEventORM.created_at)).where(
            OutboxEventORM.status == OutboxStatus.PENDING,
            OutboxEventORM.event_type == EventType.PAYMENT_REQUESTED,
        )
        result = await self._session.execute(stmt)
        oldest = result.scalar_one_or_none()
        if not oldest:
            return 0.0
        now = datetime.now(UTC)
        return max(0.0, (now - oldest).total_seconds())
