from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from payments_processor.commands.call_provider import CallProviderCommand
from payments_processor.core.errors import ProviderTimeoutError
from payments_processor.providers.strategy import ProviderStrategy

from shared.contracts import PaymentMethod, ProviderResponse
from shared.resilience.circuit_breaker import CircuitBreakerOpenError


class FakeStrategyFactory:
    def __init__(self, strategy: ProviderStrategy) -> None:
        self._strategy = strategy

    def for_method(self, method: PaymentMethod) -> ProviderStrategy:  # noqa: ARG002
        return self._strategy


class FakeBreaker:
    def __init__(self) -> None:
        self.allow_calls = 0
        self.success_calls = 0
        self.failure_calls = 0

    def allow_call(self) -> None:
        self.allow_calls += 1

    def on_success(self) -> None:
        self.success_calls += 1

    def on_failure(self) -> None:
        self.failure_calls += 1


class FakeBulkhead:
    def __init__(self) -> None:
        self.keys: list[str] = []

    @asynccontextmanager
    async def limit(self, key: str):
        self.keys.append(key)
        yield


class FakeClient:
    def __init__(
        self, responses: list[ProviderResponse] | None = None, errors: list[Exception] | None = None
    ) -> None:
        self._responses = responses or []
        self._errors = errors or []
        self.calls = 0

    async def confirm(
        self, strategy: ProviderStrategy, payload
    ) -> ProviderResponse:  # noqa: ANN001
        self.calls += 1
        if self._errors:
            raise self._errors.pop(0)
        return self._responses.pop(0)


def _payment() -> SimpleNamespace:
    return SimpleNamespace(
        payment_id=uuid4(),
        merchant_id="merchant-1",
        amount=Decimal("10.00"),
        currency="BRL",
        method=PaymentMethod.PIX,
    )


def _response() -> ProviderResponse:
    return ProviderResponse(
        provider_reference="pix-ref",
        confirmed=True,
        provider="pix-provider",
        duplicate=False,
        partial_failure=False,
    )


@pytest.mark.asyncio
async def test_execute_calls_provider_and_records_success_metrics(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    strategy = ProviderStrategy(provider_name="pix-provider", path="/providers/pix/confirm")
    breaker = FakeBreaker()
    bulkhead = FakeBulkhead()
    client = FakeClient(responses=[_response()])
    latency_records: list[tuple[float, dict[str, str]]] = []
    error_records: list[tuple[int, dict[str, str]]] = []

    monkeypatch.setattr(
        "payments_processor.commands.call_provider.provider_latency.record",
        lambda duration, attrs: latency_records.append((duration, attrs)),
    )
    monkeypatch.setattr(
        "payments_processor.commands.call_provider.provider_errors.add",
        lambda value, attrs: error_records.append((value, attrs)),
    )

    command = CallProviderCommand(
        client=client,  # type: ignore[arg-type]
        strategy_factory=FakeStrategyFactory(strategy),  # type: ignore[arg-type]
        bulkhead=bulkhead,  # type: ignore[arg-type]
        breakers={strategy.provider_name: breaker},  # type: ignore[arg-type]
    )
    result = await command.execute(_payment())

    assert result.confirmed is True
    assert client.calls == 1
    assert bulkhead.keys == ["pix-provider"]
    assert breaker.allow_calls == 1
    assert breaker.success_calls == 1
    assert breaker.failure_calls == 0
    assert latency_records and latency_records[0][1] == {"provider": "pix-provider"}
    assert error_records == []


@pytest.mark.asyncio
async def test_execute_marks_failure_and_records_error_metric_on_provider_error(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    strategy = ProviderStrategy(provider_name="pix-provider", path="/providers/pix/confirm")
    breaker = FakeBreaker()
    bulkhead = FakeBulkhead()
    client = FakeClient(errors=[ProviderTimeoutError("timeout")] * 3)
    error_records: list[tuple[int, dict[str, str]]] = []

    monkeypatch.setattr(
        "payments_processor.commands.call_provider.provider_errors.add",
        lambda value, attrs: error_records.append((value, attrs)),
    )
    monkeypatch.setattr(
        "payments_processor.commands.call_provider.provider_latency.record", lambda *_: None
    )

    command = CallProviderCommand(
        client=client,  # type: ignore[arg-type]
        strategy_factory=FakeStrategyFactory(strategy),  # type: ignore[arg-type]
        bulkhead=bulkhead,  # type: ignore[arg-type]
        breakers={strategy.provider_name: breaker},  # type: ignore[arg-type]
    )

    with pytest.raises(ProviderTimeoutError):
        await command.execute(_payment())

    assert client.calls == 3
    assert breaker.allow_calls == 1
    assert breaker.success_calls == 0
    assert breaker.failure_calls == 1
    assert error_records[0][1]["error"] == "ProviderTimeoutError"
    assert error_records[0][1]["provider"] == "pix-provider"


def test_is_transient_covers_supported_retry_exceptions() -> None:
    command = CallProviderCommand(
        client=SimpleNamespace(),  # type: ignore[arg-type]
        strategy_factory=SimpleNamespace(),  # type: ignore[arg-type]
        bulkhead=SimpleNamespace(),  # type: ignore[arg-type]
        breakers={},
    )

    assert command._is_transient(ProviderTimeoutError()) is True
    assert command._is_transient(CircuitBreakerOpenError("open")) is True
    assert command._is_transient(RuntimeError("permanent")) is False
