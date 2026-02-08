from __future__ import annotations

import asyncio

import pytest

from shared.resilience.bulkhead import Bulkhead


@pytest.mark.asyncio
async def test_bulkhead_serializes_calls_per_key_when_limit_is_one() -> None:
    bulkhead = Bulkhead(limit_per_key=1)
    active = 0
    max_active = 0

    async def guarded_call() -> None:
        nonlocal active, max_active
        async with bulkhead.limit("pix-provider"):
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.01)
            active -= 1

    await asyncio.gather(guarded_call(), guarded_call())
    assert max_active == 1


@pytest.mark.asyncio
async def test_bulkhead_allows_parallel_calls_for_different_keys() -> None:
    bulkhead = Bulkhead(limit_per_key=1)
    finished: list[str] = []

    async def guarded_call(key: str) -> None:
        async with bulkhead.limit(key):
            await asyncio.sleep(0.01)
            finished.append(key)

    await asyncio.gather(guarded_call("pix-provider"), guarded_call("ted-provider"))
    assert sorted(finished) == ["pix-provider", "ted-provider"]
