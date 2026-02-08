from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from payments_api.core.errors import AppError
from shared.logging import get_logger

logger = get_logger(__name__)
_GENERIC_INTERNAL_ERROR_MESSAGE = "Internal server error"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "application_error", extra={"extra_fields": {"error_category": exc.category.value}}
        )
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"category": exc.category.value, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unexpected_error", extra={"extra_fields": {"error_category": "unexpected"}}
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {"category": "unexpected", "message": _GENERIC_INTERNAL_ERROR_MESSAGE}
            },
        )
