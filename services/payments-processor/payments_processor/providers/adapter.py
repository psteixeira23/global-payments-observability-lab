from __future__ import annotations

import httpx

from payments_processor.core.errors import Provider5xxError, ProviderTimeoutError
from payments_processor.providers.strategy import ProviderStrategy
from shared.contracts import ProviderRequest, ProviderResponse
from shared.observability import inject_headers


class ProviderClientAdapter:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http_client = http_client

    async def confirm(
        self, strategy: ProviderStrategy, payload: ProviderRequest
    ) -> ProviderResponse:
        headers = inject_headers({"Content-Type": "application/json"})
        try:
            response = await self._http_client.post(
                strategy.path, json=payload.model_dump(mode="json"), headers=headers
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError() from exc

        if response.status_code >= 500:
            raise Provider5xxError(f"Provider returned {response.status_code}")
        response.raise_for_status()
        return ProviderResponse.model_validate(response.json())

    async def close(self) -> None:
        await self._http_client.aclose()
