from __future__ import annotations

import asyncio

import pytest

from shared.resilience.backoff import exponential_backoff
from shared.resilience.retry import retry_async


def test_exponential_backoff_without_jitter_when_random_is_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("random.uniform", lambda _a, _b: 0.0)

    first = exponential_backoff(1, base_seconds=0.1, cap_seconds=1.0, jitter=0.5)
    second = exponential_backoff(2, base_seconds=0.1, cap_seconds=1.0, jitter=0.5)

    assert first == 0.1
    assert second == 0.2


@pytest.mark.asyncio
async def test_retry_async_retries_until_success() -> None:
    attempts = 0

    async def operation() -> str:
        await asyncio.sleep(0)
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("transient")
        return "ok"

    result = await retry_async(
        operation, should_retry=lambda exc: isinstance(exc, ValueError), max_attempts=3
    )

    assert result == "ok"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_async_stops_for_non_retryable_error() -> None:
    async def operation() -> str:
        await asyncio.sleep(0)
        raise RuntimeError("fatal")

    with pytest.raises(RuntimeError):
        await retry_async(operation, should_retry=lambda _exc: False, max_attempts=3)
