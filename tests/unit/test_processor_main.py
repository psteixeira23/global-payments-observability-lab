from __future__ import annotations

from types import SimpleNamespace

import payments_processor.main as processor_main
import pytest

from shared.constants import supported_provider_names
from shared.resilience.circuit_breaker import CircuitBreaker


class FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


class FakeProviderClient:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class FakeProviderClientFactory:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.client = FakeProviderClient()

    def create(self) -> FakeProviderClient:
        return self.client


class FakeOutboxWorker:
    def __init__(
        self, settings, session_factory, provider_command, strategy_factory
    ) -> None:  # noqa: ANN001
        self.settings = settings
        self.session_factory = session_factory
        self.provider_command = provider_command
        self.strategy_factory = strategy_factory
        self.run_count = 0

    async def run_forever(self) -> None:
        self.run_count += 1


@pytest.mark.asyncio
async def test_run_initializes_worker_and_closes_resources(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    settings = SimpleNamespace(
        log_level="INFO",
        service_name="payments-processor-test",
        postgres_dsn="postgresql+asyncpg://unused",
        resolved_provider_mock_base_url="http://provider-mock:8082",
        provider_timeout_seconds=1.5,
        bulkhead_limit_per_provider=8,
        poll_interval_seconds=0.01,
        batch_size=10,
        max_event_attempts=3,
    )
    engine = FakeEngine()
    session_factory = object()
    worker_instances: list[FakeOutboxWorker] = []

    def fake_outbox_worker(*args, **kwargs):  # noqa: ANN002, ANN003
        worker = FakeOutboxWorker(*args, **kwargs)
        worker_instances.append(worker)
        return worker

    monkeypatch.setattr(processor_main, "get_settings", lambda: settings)
    monkeypatch.setattr(processor_main, "configure_logging", lambda _level: None)
    monkeypatch.setattr(processor_main, "configure_otel", lambda _service: None)
    monkeypatch.setattr(processor_main, "build_engine", lambda _dsn: engine)
    monkeypatch.setattr(processor_main, "build_session_factory", lambda _engine: session_factory)
    monkeypatch.setattr(processor_main, "ProviderClientFactory", FakeProviderClientFactory)
    monkeypatch.setattr(processor_main, "OutboxWorker", fake_outbox_worker)

    await processor_main.run()

    assert worker_instances
    worker = worker_instances[0]
    assert worker.run_count == 1
    assert worker.settings is settings
    assert worker.session_factory is session_factory
    assert isinstance(worker.provider_command._client, FakeProviderClient)  # type: ignore[attr-defined]
    assert engine.disposed is True
    assert worker.provider_command._client.closed is True  # type: ignore[attr-defined]


def test_build_provider_breakers_covers_all_supported_providers() -> None:
    breakers = processor_main._build_provider_breakers()

    assert set(breakers) == set(supported_provider_names())
    assert all(isinstance(value, CircuitBreaker) for value in breakers.values())


def test_main_handles_keyboard_interrupt(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    messages: list[str] = []

    def fake_asyncio_run(coro):  # noqa: ANN001
        coro.close()
        raise KeyboardInterrupt()

    monkeypatch.setattr(processor_main.asyncio, "run", fake_asyncio_run)
    monkeypatch.setattr(processor_main.logger, "info", lambda message: messages.append(message))

    processor_main.main()
    assert messages == ["processor_stopped"]
