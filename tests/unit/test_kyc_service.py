from __future__ import annotations

from datetime import UTC, datetime

import pytest
from payments_api.core.errors import KycDeniedError
from payments_api.services.kyc_service import KycService

from shared.contracts import CustomerORM, CustomerStatus, KycLevel, PaymentMethod


def _customer(kyc_level: KycLevel, status: CustomerStatus = CustomerStatus.ACTIVE) -> CustomerORM:
    return CustomerORM(
        customer_id="customer-1",
        kyc_level=kyc_level,
        status=status,
        created_at=datetime.now(UTC),
    )


def test_kyc_enforces_minimum_level_by_rail() -> None:
    service = KycService()

    service.enforce(_customer(KycLevel.BASIC), PaymentMethod.PIX)
    service.enforce(_customer(KycLevel.BASIC), PaymentMethod.BOLETO)
    service.enforce(_customer(KycLevel.BASIC), PaymentMethod.CARD)

    with pytest.raises(KycDeniedError):
        service.enforce(_customer(KycLevel.BASIC), PaymentMethod.TED)


def test_kyc_blocks_suspended_customer() -> None:
    service = KycService()

    with pytest.raises(KycDeniedError):
        service.enforce(
            _customer(KycLevel.FULL, status=CustomerStatus.SUSPENDED), PaymentMethod.PIX
        )
