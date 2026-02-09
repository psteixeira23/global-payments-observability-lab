from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import metrics, trace
from starlette.responses import Response

from provider_mock.api.routes_provider import router as provider_router
from provider_mock.core.config import get_settings
from provider_mock.simulation.engine import FaultConfig, ProviderSimulationEngine
from shared.logging import CorrelationMiddleware, configure_logging
from shared.observability import configure_otel, current_trace_id
from shared.utils import apply_security_headers

meter = metrics.get_meter("provider-mock")
request_counter = meter.create_counter("provider_mock_request_total")
latency = meter.create_histogram("provider_mock_latency_ms")
error_counter = meter.create_counter("provider_mock_error_total")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_otel(settings.service_name)
    app.state.engine = ProviderSimulationEngine(
        FaultConfig(
            seed=settings.random_seed,
            base_latency_ms=settings.base_latency_ms,
            latency_spike_ms=settings.latency_spike_ms,
            timeout_ms=settings.timeout_ms,
            fault_5xx_rate=settings.fault_5xx_rate,
            timeout_rate=settings.timeout_rate,
            latency_spike_rate=settings.latency_spike_rate,
            duplicate_rate=settings.duplicate_rate,
            partial_failure_rate=settings.partial_failure_rate,
        )
    )
    yield


startup_settings = get_settings()

app = FastAPI(title="provider-mock", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=startup_settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(CorrelationMiddleware)
app.include_router(provider_router)


@app.middleware("http")
async def telemetry_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    tracer = trace.get_tracer("provider-mock")
    start = time.perf_counter()
    request_counter.add(1, {"path": request.url.path, "method": request.method})
    with tracer.start_as_current_span(f"{request.method} {request.url.path}"):
        response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    latency.record(elapsed, {"path": request.url.path})
    if response.status_code >= 400:
        error_counter.add(1, {"status_code": response.status_code})
    response.headers["X-Trace-Id"] = current_trace_id()
    apply_security_headers(response)
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
