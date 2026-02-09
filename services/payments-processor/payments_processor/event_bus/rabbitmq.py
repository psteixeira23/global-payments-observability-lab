from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aio_pika

from shared.contracts import OutboxEventORM


class RabbitMqEventBusPublisher:
    def __init__(self, url: str, exchange_name: str, routing_prefix: str) -> None:
        self._url = url
        self._exchange_name = exchange_name
        self._routing_prefix = routing_prefix
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    @property
    def is_enabled(self) -> bool:
        return True

    async def publish(self, event: OutboxEventORM) -> None:
        exchange = await self._get_exchange()
        body = self._serialize_event(event)
        message = aio_pika.Message(
            body=body,
            content_type="application/json",
            message_id=str(event.event_id),
            timestamp=datetime.now(),
        )
        await exchange.publish(message, routing_key=self._routing_key(event.event_type.value))

    async def close(self) -> None:
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def _get_exchange(self) -> aio_pika.abc.AbstractExchange:
        if self._exchange:
            return self._exchange
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            self._exchange_name,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        return self._exchange

    def _serialize_event(self, event: OutboxEventORM) -> bytes:
        payload: dict[str, Any] = {
            "event_id": str(event.event_id),
            "aggregate_id": str(event.aggregate_id),
            "event_type": event.event_type.value,
            "created_at": event.created_at.isoformat(),
            "payload": event.payload,
            "attempts": event.attempts,
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def _routing_key(self, event_type: str) -> str:
        normalized = event_type.replace(".", "_").replace("-", "_").lower()
        return f"{self._routing_prefix}.{normalized}"
