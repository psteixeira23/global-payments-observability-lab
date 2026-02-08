from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import KycLevel, PaymentMethod


@dataclass(frozen=True)
class RailProfile:
    method: PaymentMethod
    provider_slug: str
    provider_name: str
    minimum_kyc_level: KycLevel


_KYC_LEVEL_RANK = {
    KycLevel.NONE: 0,
    KycLevel.BASIC: 1,
    KycLevel.FULL: 2,
}

_RAIL_PROFILES = {
    PaymentMethod.PIX: RailProfile(
        method=PaymentMethod.PIX,
        provider_slug="pix",
        provider_name="pix-provider",
        minimum_kyc_level=KycLevel.BASIC,
    ),
    PaymentMethod.BOLETO: RailProfile(
        method=PaymentMethod.BOLETO,
        provider_slug="boleto",
        provider_name="boleto-provider",
        minimum_kyc_level=KycLevel.BASIC,
    ),
    PaymentMethod.TED: RailProfile(
        method=PaymentMethod.TED,
        provider_slug="ted",
        provider_name="ted-provider",
        minimum_kyc_level=KycLevel.FULL,
    ),
    PaymentMethod.CARD: RailProfile(
        method=PaymentMethod.CARD,
        provider_slug="card",
        provider_name="card-provider",
        minimum_kyc_level=KycLevel.BASIC,
    ),
}


def get_rail_profile(method: PaymentMethod) -> RailProfile:
    return _RAIL_PROFILES[method]


def provider_slug_for_method(method: PaymentMethod) -> str:
    return get_rail_profile(method).provider_slug


def provider_name_for_method(method: PaymentMethod) -> str:
    return get_rail_profile(method).provider_name


def provider_confirm_path_for_method(method: PaymentMethod) -> str:
    slug = provider_slug_for_method(method)
    return f"/providers/{slug}/confirm"


def minimum_kyc_level_for_method(method: PaymentMethod) -> KycLevel:
    return get_rail_profile(method).minimum_kyc_level


def kyc_level_rank(level: KycLevel) -> int:
    return _KYC_LEVEL_RANK[level]


def supported_provider_names() -> tuple[str, ...]:
    return tuple(profile.provider_name for profile in _RAIL_PROFILES.values())
