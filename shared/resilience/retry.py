from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from shared.resilience.backoff import exponential_backoff

T = TypeVar("T")


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    should_retry: Callable[[Exception], bool],
    max_attempts: int = 3,
    base_seconds: float = 0.05,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as exc:  # noqa: BLE001
            if not should_retry(exc) or attempt == max_attempts:
                raise
            last_error = exc
            await asyncio.sleep(exponential_backoff(attempt, base_seconds=base_seconds))
    if last_error:
        raise last_error
    raise RuntimeError("retry_async reached an invalid state")
