from __future__ import annotations

import httpx

from payments_processor.providers.adapter import ProviderClientAdapter


class ProviderClientFactory:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds

    def create(self) -> ProviderClientAdapter:
        client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_seconds)
        return ProviderClientAdapter(client)
