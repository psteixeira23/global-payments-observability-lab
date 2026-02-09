from __future__ import annotations

import importlib
import json
from datetime import datetime
from typing import Any

from shared.contracts import OutboxEventORM


class KafkaEventBusPublisher:
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._producer: Any | None = None

    @property
    def is_enabled(self) -> bool:
        return True

    async def publish(self, event: OutboxEventORM) -> None:
        producer = await self._get_producer()
        message = self._build_message(event)
        key = self._routing_key(event.event_type.value).encode("utf-8")
        await producer.send_and_wait(self._topic, value=message, key=key)

    async def close(self) -> None:
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None

    async def _get_producer(self) -> Any:
        if self._producer is not None:
            return self._producer
        self._producer = self._build_producer()
        await self._producer.start()
        return self._producer

    def _build_producer(self) -> Any:
        try:
            aiokafka_module = importlib.import_module("aiokafka")
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(
                "aiokafka is required for EVENT_BUS_BACKEND=kafka. Install project dependencies with Poetry."
            ) from exc
        producer_cls = aiokafka_module.AIOKafkaProducer
        return producer_cls(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda payload: json.dumps(payload, separators=(",", ":")).encode(
                "utf-8"
            ),
        )

    def _build_message(self, event: OutboxEventORM) -> dict[str, Any]:
        return {
            "event_id": str(event.event_id),
            "aggregate_id": str(event.aggregate_id),
            "event_type": event.event_type.value,
            "created_at": event.created_at.isoformat(),
            "payload": event.payload,
            "attempts": event.attempts,
            "published_at": datetime.now().isoformat(),
        }

    def _routing_key(self, event_type: str) -> str:
        return event_type.replace(".", "_").replace("-", "_").lower()
