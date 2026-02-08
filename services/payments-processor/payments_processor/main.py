from __future__ import annotations

import asyncio

from payments_processor.commands.call_provider import CallProviderCommand
from payments_processor.core.config import get_settings
from payments_processor.db.session import build_engine, build_session_factory
from payments_processor.providers.factory import ProviderClientFactory
from payments_processor.providers.strategy import ProviderStrategyFactory
from payments_processor.workers.outbox_worker import OutboxWorker
from shared.constants import supported_provider_names
from shared.logging import configure_logging, get_logger
from shared.observability import configure_otel
from shared.resilience import Bulkhead, CircuitBreaker, CircuitBreakerConfig

logger = get_logger(__name__)


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_otel(settings.service_name)

    engine = build_engine(settings.postgres_dsn)
    session_factory = build_session_factory(engine)

    strategy_factory = ProviderStrategyFactory()
    provider_client = ProviderClientFactory(
        base_url=settings.resolved_provider_mock_base_url,
        timeout_seconds=settings.provider_timeout_seconds,
    ).create()
    breakers = _build_provider_breakers()
    bulkhead = Bulkhead(limit_per_key=settings.bulkhead_limit_per_provider)

    command = CallProviderCommand(provider_client, strategy_factory, bulkhead, breakers)
    worker = OutboxWorker(settings, session_factory, command, strategy_factory)

    try:
        await worker.run_forever()
    finally:
        await provider_client.close()
        await engine.dispose()


def _build_provider_breakers() -> dict[str, CircuitBreaker]:
    return {
        provider_name: CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=3, recovery_timeout_seconds=5)
        )
        for provider_name in supported_provider_names()
    }


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("processor_stopped")


if __name__ == "__main__":
    main()
