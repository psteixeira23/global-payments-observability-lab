from __future__ import annotations

from dataclasses import dataclass

from shared.constants import provider_confirm_path_for_method, provider_name_for_method
from shared.contracts import PaymentMethod


@dataclass(frozen=True)
class ProviderStrategy:
    provider_name: str
    path: str


class ProviderStrategyFactory:
    def for_method(self, method: PaymentMethod) -> ProviderStrategy:
        return ProviderStrategy(
            provider_name=provider_name_for_method(method),
            path=provider_confirm_path_for_method(method),
        )
