from __future__ import annotations

from uuid import uuid4

import pytest
from provider_mock.simulation.engine import FaultConfig, ProviderSimulationEngine

from shared.contracts import PaymentMethod, ProviderRequest


def _payload() -> ProviderRequest:
    return ProviderRequest(
        payment_id=uuid4(),
        merchant_id="merchant-1",
        amount="10.00",
        currency="BRL",
        method=PaymentMethod.PIX,
    )


def _config(**overrides: float | int) -> FaultConfig:
    return FaultConfig(
        seed=int(overrides.get("seed", 42)),
        base_latency_ms=int(overrides.get("base_latency_ms", 10)),
        latency_spike_ms=int(overrides.get("latency_spike_ms", 100)),
        timeout_ms=int(overrides.get("timeout_ms", 500)),
        fault_5xx_rate=float(overrides.get("fault_5xx_rate", 0.0)),
        timeout_rate=float(overrides.get("timeout_rate", 0.0)),
        latency_spike_rate=float(overrides.get("latency_spike_rate", 0.0)),
        duplicate_rate=float(overrides.get("duplicate_rate", 0.0)),
        partial_failure_rate=float(overrides.get("partial_failure_rate", 0.0)),
    )


@pytest.mark.asyncio
async def test_simulate_returns_successful_provider_response() -> None:
    engine = ProviderSimulationEngine(_config())
    response = await engine.simulate("pix", _payload())
    assert response.provider == "pix-provider"
    assert response.confirmed is True
    assert response.duplicate is False
    assert response.partial_failure is False


@pytest.mark.asyncio
async def test_simulate_raises_timeout_when_timeout_rate_is_forced() -> None:
    engine = ProviderSimulationEngine(_config(timeout_rate=1.0))
    with pytest.raises(TimeoutError, match="Simulated provider timeout"):
        await engine.simulate("pix", _payload())


@pytest.mark.asyncio
async def test_simulate_raises_runtime_error_when_5xx_rate_is_forced() -> None:
    engine = ProviderSimulationEngine(_config(fault_5xx_rate=1.0))
    with pytest.raises(RuntimeError, match="Simulated provider 5xx"):
        await engine.simulate("pix", _payload())


@pytest.mark.asyncio
async def test_simulate_marks_duplicate_and_partial_failure_when_forced() -> None:
    engine = ProviderSimulationEngine(
        _config(duplicate_rate=1.0, partial_failure_rate=1.0, timeout_rate=0.0, fault_5xx_rate=0.0)
    )
    response = await engine.simulate("pix", _payload())
    assert response.duplicate is True
    assert response.partial_failure is True
    assert response.confirmed is False


def test_latency_seconds_includes_spike_when_rate_forced() -> None:
    engine = ProviderSimulationEngine(
        _config(base_latency_ms=20, latency_spike_ms=80, latency_spike_rate=1.0)
    )
    latency_seconds = engine._latency_seconds(engine._rng("pix", uuid4()))  # noqa: SLF001
    assert latency_seconds == 0.1
