from __future__ import annotations

from typing import Protocol

from shared.contracts import OutboxEventORM


class EventBusPublisher(Protocol):
    @property
    def is_enabled(self) -> bool: ...

    async def publish(self, event: OutboxEventORM) -> None: ...

    async def close(self) -> None: ...
