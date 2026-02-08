from __future__ import annotations

import time

from payments_processor.core.errors import Provider5xxError, ProviderTimeoutError
from payments_processor.core.metrics import provider_errors, provider_latency
from payments_processor.providers.adapter import ProviderClientAdapter
from payments_processor.providers.strategy import ProviderStrategy, ProviderStrategyFactory
from shared.contracts import PaymentORM, ProviderRequest, ProviderResponse
from shared.resilience import Bulkhead, CircuitBreaker, CircuitBreakerOpenError, retry_async


class CallProviderCommand:
    def __init__(
        self,
        client: ProviderClientAdapter,
        strategy_factory: ProviderStrategyFactory,
        bulkhead: Bulkhead,
        breakers: dict[str, CircuitBreaker],
    ) -> None:
        self._client = client
        self._strategy_factory = strategy_factory
        self._bulkhead = bulkhead
        self._breakers = breakers

    async def execute(self, payment: PaymentORM) -> ProviderResponse:
        strategy = self._strategy_factory.for_method(payment.method)
        breaker = self._breakers[strategy.provider_name]
        breaker.allow_call()
        async with self._bulkhead.limit(strategy.provider_name):
            start = time.perf_counter()
            try:
                response = await retry_async(
                    lambda: self._call_once(strategy, payment),
                    should_retry=self._is_transient,
                    max_attempts=3,
                    base_seconds=0.05,
                )
            except Exception as exc:  # noqa: BLE001
                breaker.on_failure()
                provider_errors.add(
                    1, {"provider": strategy.provider_name, "error": type(exc).__name__}
                )
                raise
        breaker.on_success()
        duration_ms = (time.perf_counter() - start) * 1000
        provider_latency.record(duration_ms, {"provider": strategy.provider_name})
        return response

    async def _call_once(self, strategy: ProviderStrategy, payment: PaymentORM) -> ProviderResponse:
        request = ProviderRequest(
            payment_id=payment.payment_id,
            merchant_id=payment.merchant_id,
            amount=payment.amount,
            currency=payment.currency,
            method=payment.method,
        )
        return await self._client.confirm(strategy, request)

    def _is_transient(self, exc: Exception) -> bool:
        return isinstance(exc, ProviderTimeoutError | Provider5xxError | CircuitBreakerOpenError)
