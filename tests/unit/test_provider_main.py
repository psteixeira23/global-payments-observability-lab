from __future__ import annotations

from types import SimpleNamespace

import provider_mock.main as provider_main
from provider_mock.simulation.engine import FaultConfig, ProviderSimulationEngine

from tests.helpers import create_test_client


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        service_name="provider-mock-test",
        log_level="INFO",
        random_seed=7,
        base_latency_ms=10,
        latency_spike_ms=100,
        timeout_ms=500,
        fault_5xx_rate=0.1,
        timeout_rate=0.2,
        latency_spike_rate=0.3,
        duplicate_rate=0.4,
        partial_failure_rate=0.5,
    )


def test_provider_app_lifespan_initializes_simulation_engine(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(provider_main, "get_settings", _settings)
    monkeypatch.setattr(provider_main, "configure_logging", lambda _level: None)
    monkeypatch.setattr(provider_main, "configure_otel", lambda _service: None)

    with create_test_client(provider_main.app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "X-Trace-Id" in response.headers
        assert "/providers/pix/confirm" in client.get("/openapi.json").json()["paths"]

        engine = client.app.state.engine
        assert isinstance(engine, ProviderSimulationEngine)
        assert engine._config == FaultConfig(  # type: ignore[attr-defined]
            seed=7,
            base_latency_ms=10,
            latency_spike_ms=100,
            timeout_ms=500,
            fault_5xx_rate=0.1,
            timeout_rate=0.2,
            latency_spike_rate=0.3,
            duplicate_rate=0.4,
            partial_failure_rate=0.5,
        )
