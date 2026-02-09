from __future__ import annotations

import importlib
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from payments_processor.event_bus.kafka import KafkaEventBusPublisher


def _event():  # noqa: ANN202
    return SimpleNamespace(
        event_id=uuid4(),
        aggregate_id=uuid4(),
        event_type=SimpleNamespace(value="PaymentConfirmed"),
        created_at=datetime.now(UTC),
        payload={"status": "CONFIRMED"},
        attempts=1,
    )


def test_kafka_event_bus_message_shape() -> None:
    publisher = KafkaEventBusPublisher("kafka:9092", "payments.domain-events")
    message = publisher._build_message(_event())  # noqa: SLF001

    assert "event_id" in message
    assert "aggregate_id" in message
    assert message["event_type"] == "PaymentConfirmed"
    assert message["payload"]["status"] == "CONFIRMED"
    assert "published_at" in message


def test_kafka_event_bus_routing_key_normalization() -> None:
    publisher = KafkaEventBusPublisher("kafka:9092", "payments.domain-events")
    routing_key = publisher._routing_key("Payment-Confirmed")  # noqa: SLF001
    assert routing_key == "payment_confirmed"


class FakeProducer:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.sent: tuple[str, dict, bytes] | None = None

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def send_and_wait(self, topic: str, *, value: dict, key: bytes) -> None:
        self.sent = (topic, value, key)


@pytest.mark.asyncio
async def test_publish_sends_message_with_normalized_key() -> None:
    publisher = KafkaEventBusPublisher("kafka:9092", "payments.domain-events")
    fake = FakeProducer()
    publisher._producer = fake  # type: ignore[assignment]  # noqa: SLF001

    await publisher.publish(_event())

    assert fake.sent is not None
    topic, value, key = fake.sent
    assert topic == "payments.domain-events"
    assert value["event_type"] == "PaymentConfirmed"
    assert key == b"paymentconfirmed"


@pytest.mark.asyncio
async def test_get_producer_builds_and_starts_only_once(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = KafkaEventBusPublisher("kafka:9092", "payments.domain-events")
    fake = FakeProducer()
    calls = {"build": 0}

    def fake_build() -> FakeProducer:
        calls["build"] += 1
        return fake

    monkeypatch.setattr(publisher, "_build_producer", fake_build)

    producer_a = await publisher._get_producer()  # noqa: SLF001
    producer_b = await publisher._get_producer()  # noqa: SLF001

    assert producer_a is producer_b
    assert calls["build"] == 1
    assert fake.started is True


@pytest.mark.asyncio
async def test_close_stops_existing_producer() -> None:
    publisher = KafkaEventBusPublisher("kafka:9092", "payments.domain-events")
    fake = FakeProducer()
    publisher._producer = fake  # type: ignore[assignment]  # noqa: SLF001

    await publisher.close()

    assert fake.stopped is True
    assert publisher._producer is None  # noqa: SLF001


@pytest.mark.asyncio
async def test_close_is_noop_when_producer_not_initialized() -> None:
    publisher = KafkaEventBusPublisher("kafka:9092", "payments.domain-events")
    await publisher.close()
    assert publisher._producer is None  # noqa: SLF001


def test_build_producer_raises_runtime_error_when_aiokafka_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publisher = KafkaEventBusPublisher("kafka:9092", "payments.domain-events")

    def raise_module_not_found(_: str) -> None:
        raise ModuleNotFoundError("aiokafka")

    monkeypatch.setattr(importlib, "import_module", raise_module_not_found)

    with pytest.raises(RuntimeError, match="aiokafka is required"):
        publisher._build_producer()  # noqa: SLF001
