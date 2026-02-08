from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import APIRouter, FastAPI


def build_app_with_router(router: APIRouter) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


@contextmanager
def override_dependencies(
    app: FastAPI,
    overrides: dict[Any, Any],
) -> Iterator[None]:
    app.dependency_overrides.update(overrides)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
