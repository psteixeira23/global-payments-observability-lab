from __future__ import annotations

import asyncio

from opentelemetry import trace
from opentelemetry.context import Context
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payments_processor.commands.call_provider import CallProviderCommand
from payments_processor.commands.finalize_payment import FinalizePaymentCommand
from payments_processor.commands.mark_processing import MarkProcessingCommand
from payments_processor.core.config import Settings
from payments_processor.core.errors import ProcessorError
from payments_processor.core.metrics import outbox_backlog, outbox_lag_seconds
from payments_processor.providers.strategy import ProviderStrategyFactory
from payments_processor.repositories.outbox_repository import OutboxRepository
from payments_processor.repositories.payment_repository import PaymentRepository
from shared.contracts import OutboxEventORM, PaymentFailureReason, PaymentORM, ProviderName
from shared.logging import get_logger
from shared.observability import extract_context_from_headers
from shared.resilience.backoff import exponential_backoff

logger = get_logger(__name__)


class OutboxWorker:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        provider_command: CallProviderCommand,
        strategy_factory: ProviderStrategyFactory,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._provider_command = provider_command
        self._strategy_factory = strategy_factory
        self._tracer = trace.get_tracer(__name__)

    async def run_forever(self) -> None:
        while True:
            try:
                await self.run_once()
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "worker_iteration_failed",
                    extra={"extra_fields": {"error_type": type(exc).__name__}},
                )
            await asyncio.sleep(self._settings.poll_interval_seconds)

    async def run_once(self) -> None:
        async with self._session_factory() as session:
            outbox_repo = OutboxRepository(session)
            outbox_backlog.record(await outbox_repo.backlog_size())
            outbox_lag_seconds.record(await outbox_repo.oldest_pending_lag_seconds())
            events = await outbox_repo.fetch_pending_requested(self._settings.batch_size)
            for event in events:
                await self._process_event(session, event)

    async def _process_event(self, session: AsyncSession, event: OutboxEventORM) -> None:
        with self._tracer.start_as_current_span(
            "outbox_process", context=self._extract_context(event)
        ):
            payment_repo = PaymentRepository(session)
            outbox_repo = OutboxRepository(session)
            finalize = FinalizePaymentCommand(payment_repo, outbox_repo)
            payment = await payment_repo.get_by_id(event.aggregate_id)
            if not payment:
                await self._mark_missing_payment(outbox_repo, event)
                await session.commit()
                return

            if not await MarkProcessingCommand(payment_repo).execute(payment):
                await outbox_repo.mark_sent(event.event_id)
                await session.commit()
                return

            await self._process_payment_event(session, event, payment, outbox_repo, finalize)

    def _extract_context(self, event: OutboxEventORM) -> Context | None:
        traceparent = event.payload.get("traceparent")
        if not traceparent:
            return None
        return extract_context_from_headers({"traceparent": traceparent})

    async def _mark_missing_payment(
        self, outbox_repo: OutboxRepository, event: OutboxEventORM
    ) -> None:
        await outbox_repo.mark_failed(event.event_id, event.attempts + 1)

    async def _process_payment_event(
        self,
        session: AsyncSession,
        event: OutboxEventORM,
        payment: PaymentORM,
        outbox_repo: OutboxRepository,
        finalize: FinalizePaymentCommand,
    ) -> None:
        try:
            response = await self._provider_command.execute(payment)
            if response.confirmed and not response.partial_failure:
                await finalize.confirm(payment, response.provider, response.provider_reference)
            else:
                await finalize.fail(
                    payment,
                    response.provider,
                    PaymentFailureReason.PROVIDER_PARTIAL_FAILURE.value,
                    "Partial failure",
                )
            await outbox_repo.mark_sent(event.event_id)
        except ProcessorError as exc:
            await self._handle_processor_error(event, payment, outbox_repo, finalize, exc)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "unexpected_processor_error",
                extra={
                    "extra_fields": {
                        "payment_id": str(payment.payment_id),
                        "error_type": type(exc).__name__,
                    }
                },
            )
            await finalize.fail(
                payment,
                ProviderName.UNKNOWN.value,
                PaymentFailureReason.UNEXPECTED.value,
                "Unexpected processor failure",
            )
            await outbox_repo.mark_failed(event.event_id, event.attempts + 1)
        await session.commit()

    async def _handle_processor_error(
        self,
        event: OutboxEventORM,
        payment: PaymentORM,
        outbox_repo: OutboxRepository,
        finalize: FinalizePaymentCommand,
        error: ProcessorError,
    ) -> None:
        attempts = event.attempts + 1
        provider = self._strategy_factory.for_method(payment.method).provider_name
        if attempts >= self._settings.max_event_attempts:
            await finalize.fail(payment, provider, error.category.value, error.message)
            await outbox_repo.mark_failed(event.event_id, attempts)
            return
        delay = exponential_backoff(attempts, base_seconds=0.5, cap_seconds=5.0)
        await outbox_repo.reschedule(event.event_id, attempts=attempts, delay_seconds=delay)
