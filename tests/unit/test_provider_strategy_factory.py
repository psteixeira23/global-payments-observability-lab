from __future__ import annotations

import pytest
from payments_processor.providers.adapter import ProviderClientAdapter
from payments_processor.providers.factory import ProviderClientFactory
from payments_processor.providers.strategy import ProviderStrategyFactory

from shared.contracts import PaymentMethod


def test_strategy_factory_selects_all_supported_rails() -> None:
    factory = ProviderStrategyFactory()

    assert factory.for_method(PaymentMethod.PIX).path == "/providers/pix/confirm"
    assert factory.for_method(PaymentMethod.BOLETO).path == "/providers/boleto/confirm"
    assert factory.for_method(PaymentMethod.TED).path == "/providers/ted/confirm"
    assert factory.for_method(PaymentMethod.CARD).path == "/providers/card/confirm"


@pytest.mark.asyncio
async def test_provider_client_factory_builds_adapter() -> None:
    factory = ProviderClientFactory(base_url="http://localhost:8082", timeout_seconds=1.0)

    adapter = factory.create()

    assert isinstance(adapter, ProviderClientAdapter)
    await adapter.close()
