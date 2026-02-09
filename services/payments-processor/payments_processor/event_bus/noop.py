from __future__ import annotations

from shared.contracts import OutboxEventORM


class NoopEventBusPublisher:
    @property
    def is_enabled(self) -> bool:
        return False

    async def publish(self, event: OutboxEventORM) -> None:  # noqa: ARG002
        return None

    async def close(self) -> None:
        return None
