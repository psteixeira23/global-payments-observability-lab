from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from shared.logging.fields import (
    ACCOUNT_ID,
    CUSTOMER_ID,
    IDEMPOTENCY_KEY,
    MERCHANT_ID,
    RAIL,
    TRACE_ID,
)
from shared.logging.logger import clear_correlation_context, set_correlation_context
from shared.observability.propagation import current_trace_id


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = current_trace_id() or ""
        set_correlation_context(
            {
                TRACE_ID: trace_id,
                IDEMPOTENCY_KEY: request.headers.get("Idempotency-Key", ""),
                MERCHANT_ID: request.headers.get("X-Merchant-Id", ""),
                CUSTOMER_ID: request.headers.get("X-Customer-Id", ""),
                ACCOUNT_ID: request.headers.get("X-Account-Id", ""),
                RAIL: request.headers.get("X-Rail", ""),
            }
        )
        try:
            response = await call_next(request)
            return response
        finally:
            clear_correlation_context()
