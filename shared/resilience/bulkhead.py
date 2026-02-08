from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class Bulkhead:
    def __init__(self, limit_per_key: int = 10) -> None:
        self._limit_per_key = limit_per_key
        self._locks: defaultdict[str, asyncio.Semaphore] = defaultdict(self._new_semaphore)

    def _new_semaphore(self) -> asyncio.Semaphore:
        return asyncio.Semaphore(self._limit_per_key)

    @asynccontextmanager
    async def limit(self, key: str) -> AsyncIterator[None]:
        semaphore = self._locks[key]
        async with semaphore:
            yield
