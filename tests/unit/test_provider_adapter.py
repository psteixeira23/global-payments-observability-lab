from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from payments_processor.core.errors import Provider5xxError, ProviderTimeoutError
from payments_processor.providers.adapter import ProviderClientAdapter
from payments_processor.providers.strategy import ProviderStrategy

from shared.contracts import PaymentMethod, ProviderRequest


class FakeHttpClient:
    def __init__(self) -> None:
        self.closed = False
        self.next_response: httpx.Response | None = None
        self.next_error: Exception | None = None
        self.last_request: dict[str, object] | None = None

    async def post(
        self, path: str, *, json: dict, headers: dict[str, str]
    ) -> httpx.Response:  # noqa: A002
        self.last_request = {"path": path, "json": json, "headers": headers}
        if self.next_error:
            raise self.next_error
        assert self.next_response is not None
        return self.next_response

    async def aclose(self) -> None:
        self.closed = True


def _provider_request() -> ProviderRequest:
    return ProviderRequest(
        payment_id=uuid4(),
        merchant_id="merchant-1",
        amount="10.00",
        currency="BRL",
        method=PaymentMethod.PIX,
    )


def _strategy() -> ProviderStrategy:
    return ProviderStrategy(provider_name="pix-provider", path="/providers/pix/confirm")


@pytest.mark.asyncio
async def test_confirm_sends_payload_with_injected_headers(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_client = FakeHttpClient()
    request = httpx.Request("POST", "http://provider-mock/providers/pix/confirm")
    fake_client.next_response = httpx.Response(
        200,
        request=request,
        json={
            "provider_reference": "pix-ref-1",
            "confirmed": True,
            "provider": "pix-provider",
            "duplicate": False,
            "partial_failure": False,
        },
    )
    monkeypatch.setattr(
        "payments_processor.providers.adapter.inject_headers",
        lambda headers: {**headers, "traceparent": "00-abc-abc-01"},
    )

    adapter = ProviderClientAdapter(fake_client)  # type: ignore[arg-type]
    response = await adapter.confirm(_strategy(), _provider_request())

    assert response.provider == "pix-provider"
    assert fake_client.last_request is not None
    assert fake_client.last_request["path"] == "/providers/pix/confirm"
    assert fake_client.last_request["headers"]["traceparent"] == "00-abc-abc-01"


@pytest.mark.asyncio
async def test_confirm_maps_timeout_exception_to_provider_timeout_error() -> None:
    fake_client = FakeHttpClient()
    fake_client.next_error = httpx.TimeoutException("timeout")
    adapter = ProviderClientAdapter(fake_client)  # type: ignore[arg-type]

    with pytest.raises(ProviderTimeoutError):
        await adapter.confirm(_strategy(), _provider_request())


@pytest.mark.asyncio
async def test_confirm_maps_5xx_to_provider_5xx_error() -> None:
    fake_client = FakeHttpClient()
    request = httpx.Request("POST", "http://provider-mock/providers/pix/confirm")
    fake_client.next_response = httpx.Response(503, request=request, json={"detail": "down"})
    adapter = ProviderClientAdapter(fake_client)  # type: ignore[arg-type]

    with pytest.raises(Provider5xxError, match="Provider returned 503"):
        await adapter.confirm(_strategy(), _provider_request())


@pytest.mark.asyncio
async def test_confirm_propagates_non_5xx_http_status_errors() -> None:
    fake_client = FakeHttpClient()
    request = httpx.Request("POST", "http://provider-mock/providers/pix/confirm")
    fake_client.next_response = httpx.Response(404, request=request, json={"detail": "not found"})
    adapter = ProviderClientAdapter(fake_client)  # type: ignore[arg-type]

    with pytest.raises(httpx.HTTPStatusError):
        await adapter.confirm(_strategy(), _provider_request())


@pytest.mark.asyncio
async def test_close_delegates_to_http_client() -> None:
    fake_client = FakeHttpClient()
    adapter = ProviderClientAdapter(fake_client)  # type: ignore[arg-type]

    await adapter.close()

    assert fake_client.closed is True
