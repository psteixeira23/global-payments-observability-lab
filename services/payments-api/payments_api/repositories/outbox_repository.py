from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts import EventType, OutboxEventORM, OutboxStatus


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_event(self, *, aggregate_id: UUID, event_type: EventType, payload: dict) -> OutboxEventORM:
        event = OutboxEventORM(
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            status=OutboxStatus.PENDING,
        )
        self._session.add(event)
        return event
