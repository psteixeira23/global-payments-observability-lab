from __future__ import annotations

from payments_api.core.errors import KycDeniedError
from shared.constants import kyc_level_rank, minimum_kyc_level_for_method
from shared.contracts import CustomerORM, CustomerStatus, KycLevel, PaymentMethod


class KycService:
    def enforce(self, customer: CustomerORM, rail: PaymentMethod) -> None:
        if customer.status != CustomerStatus.ACTIVE:
            raise KycDeniedError("Customer is suspended")
        required = self._resolve_minimum_kyc(rail)
        if kyc_level_rank(customer.kyc_level) < kyc_level_rank(required):
            raise KycDeniedError(
                f"Customer KYC level {customer.kyc_level.value} is below required {required.value}"
            )

    def _resolve_minimum_kyc(self, rail: PaymentMethod) -> KycLevel:
        try:
            return minimum_kyc_level_for_method(rail)
        except KeyError as exc:
            raise KycDeniedError(f"Unsupported payment rail for KYC checks: {rail.value}") from exc
