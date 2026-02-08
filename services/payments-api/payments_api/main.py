from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from opentelemetry import trace
from redis.asyncio import from_url as redis_from_url
from starlette.responses import Response

from payments_api.api.routes_payments import router as payments_router
from payments_api.core.config import get_settings
from payments_api.core.error_handlers import register_error_handlers
from payments_api.core.metrics import error_counter, latency_histogram, request_counter
from payments_api.db.session import build_engine, build_session_factory, init_db
from shared.logging import CorrelationMiddleware, configure_logging
from shared.observability import configure_otel, current_trace_id


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_otel(settings.service_name)

    engine = build_engine(settings.postgres_dsn)
    session_factory = build_session_factory(engine)
    redis_client = redis_from_url(settings.redis_url, decode_responses=True)

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.redis_client = redis_client

    if settings.app_env == "local":
        await init_db(engine)

    yield

    await redis_client.close()
    await engine.dispose()


app = FastAPI(title="payments-api", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationMiddleware)
register_error_handlers(app)
app.include_router(payments_router)


@app.middleware("http")
async def telemetry_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    tracer = trace.get_tracer("payments-api")
    start = time.perf_counter()
    request_counter.add(1, {"path": request.url.path, "method": request.method})

    with tracer.start_as_current_span(f"{request.method} {request.url.path}"):
        response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000
    latency_histogram.record(duration_ms, {"path": request.url.path, "method": request.method})
    if response.status_code >= 400:
        error_counter.add(
            1,
            {
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
            },
        )

    response.headers["X-Trace-Id"] = current_trace_id()
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
