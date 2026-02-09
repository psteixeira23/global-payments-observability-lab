from __future__ import annotations

from types import SimpleNamespace

import pytest
from payments_processor.event_bus import NoopEventBusPublisher, build_event_bus_publisher


def _settings(**overrides):  # noqa: ANN003
    defaults = {
        "event_bus_backend": "none",
        "event_bus_url": None,
        "event_bus_exchange": "payments.events",
        "event_bus_routing_prefix": "payments",
        "event_bus_kafka_bootstrap_servers": "kafka:9092",
        "event_bus_kafka_topic": "payments.domain-events",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_event_bus_factory_returns_noop_by_default() -> None:
    publisher = build_event_bus_publisher(_settings())
    assert isinstance(publisher, NoopEventBusPublisher)
    assert publisher.is_enabled is False


def test_event_bus_factory_requires_url_for_rabbitmq() -> None:
    with pytest.raises(ValueError, match="EVENT_BUS_URL"):
        build_event_bus_publisher(_settings(event_bus_backend="rabbitmq", event_bus_url=None))


def test_event_bus_factory_requires_bootstrap_for_kafka() -> None:
    with pytest.raises(ValueError, match="EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS"):
        build_event_bus_publisher(
            _settings(event_bus_backend="kafka", event_bus_kafka_bootstrap_servers="")
        )


def test_event_bus_factory_returns_kafka_publisher() -> None:
    publisher = build_event_bus_publisher(_settings(event_bus_backend="kafka"))
    assert publisher.__class__.__name__ == "KafkaEventBusPublisher"
    assert publisher.is_enabled is True


def test_event_bus_factory_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unsupported event bus backend"):
        build_event_bus_publisher(_settings(event_bus_backend="unknown"))
