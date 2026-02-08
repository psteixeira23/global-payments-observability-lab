from __future__ import annotations

from shared.constants import (
    minimum_kyc_level_for_method,
    provider_confirm_path_for_method,
    provider_name_for_method,
    provider_slug_for_method,
    supported_provider_names,
)
from shared.contracts import KycLevel, PaymentMethod


def test_minimum_kyc_level_mapping_by_method() -> None:
    assert minimum_kyc_level_for_method(PaymentMethod.PIX) == KycLevel.BASIC
    assert minimum_kyc_level_for_method(PaymentMethod.BOLETO) == KycLevel.BASIC
    assert minimum_kyc_level_for_method(PaymentMethod.TED) == KycLevel.FULL
    assert minimum_kyc_level_for_method(PaymentMethod.CARD) == KycLevel.BASIC


def test_provider_routing_metadata_by_method() -> None:
    assert provider_slug_for_method(PaymentMethod.PIX) == "pix"
    assert provider_name_for_method(PaymentMethod.PIX) == "pix-provider"
    assert provider_confirm_path_for_method(PaymentMethod.PIX) == "/providers/pix/confirm"


def test_supported_provider_names_are_unique() -> None:
    provider_names = supported_provider_names()
    assert len(provider_names) == 4
    assert len(set(provider_names)) == len(provider_names)
