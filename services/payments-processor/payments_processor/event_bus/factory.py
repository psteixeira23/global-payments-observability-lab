from __future__ import annotations

from payments_processor.core.config import Settings
from payments_processor.event_bus.contracts import EventBusPublisher
from payments_processor.event_bus.noop import NoopEventBusPublisher


def build_event_bus_publisher(settings: Settings) -> EventBusPublisher:
    backend = settings.event_bus_backend.strip().lower()
    if backend == "none":
        return NoopEventBusPublisher()
    if backend == "rabbitmq":
        if not settings.event_bus_url:
            raise ValueError("EVENT_BUS_URL must be set when EVENT_BUS_BACKEND=rabbitmq")
        from payments_processor.event_bus.rabbitmq import RabbitMqEventBusPublisher

        return RabbitMqEventBusPublisher(
            url=settings.event_bus_url,
            exchange_name=settings.event_bus_exchange,
            routing_prefix=settings.event_bus_routing_prefix,
        )
    if backend == "kafka":
        if not settings.event_bus_kafka_bootstrap_servers:
            raise ValueError(
                "EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS must be set when EVENT_BUS_BACKEND=kafka"
            )
        from payments_processor.event_bus.kafka import KafkaEventBusPublisher

        return KafkaEventBusPublisher(
            bootstrap_servers=settings.event_bus_kafka_bootstrap_servers,
            topic=settings.event_bus_kafka_topic,
        )
    raise ValueError(f"Unsupported event bus backend: {settings.event_bus_backend}")
