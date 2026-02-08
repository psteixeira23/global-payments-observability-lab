from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from uuid import UUID

from shared.contracts import ProviderRequest, ProviderResponse


@dataclass(frozen=True)
class FaultConfig:
    seed: int
    base_latency_ms: int
    latency_spike_ms: int
    timeout_ms: int
    fault_5xx_rate: float
    timeout_rate: float
    latency_spike_rate: float
    duplicate_rate: float
    partial_failure_rate: float


class ProviderSimulationEngine:
    def __init__(self, config: FaultConfig) -> None:
        self._config = config

    async def simulate(self, method: str, payload: ProviderRequest) -> ProviderResponse:
        rng = self._rng(method, payload.payment_id)
        await asyncio.sleep(self._latency_seconds(rng))
        if rng.random() < self._config.timeout_rate:
            await asyncio.sleep(self._config.timeout_ms / 1000)
            raise TimeoutError("Simulated provider timeout")
        if rng.random() < self._config.fault_5xx_rate:
            raise RuntimeError("Simulated provider 5xx")
        duplicate = rng.random() < self._config.duplicate_rate
        partial_failure = rng.random() < self._config.partial_failure_rate
        return ProviderResponse(
            provider_reference=f"{method}-{payload.payment_id}",
            confirmed=not partial_failure,
            provider=f"{method}-provider",
            duplicate=duplicate,
            partial_failure=partial_failure,
        )

    def _rng(self, method: str, payment_id: UUID) -> random.Random:
        return random.Random(f"{self._config.seed}:{method}:{payment_id}")

    def _latency_seconds(self, rng: random.Random) -> float:
        latency_ms = self._config.base_latency_ms
        if rng.random() < self._config.latency_spike_rate:
            latency_ms += self._config.latency_spike_ms
        return latency_ms / 1000
