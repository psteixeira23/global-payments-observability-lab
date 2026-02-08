from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from shared.contracts import CreatePaymentRequest, PaymentMethod


def test_create_payment_request_requires_enum_value_for_method() -> None:
    with pytest.raises(ValidationError):
        CreatePaymentRequest(
            amount=Decimal("10.00"),
            currency="brl",
            method="pix",
        )


def test_create_payment_request_normalizes_currency() -> None:
    request = CreatePaymentRequest(
        amount=Decimal("10.00"),
        currency="usd",
        method=PaymentMethod.BOLETO,
    )
    assert request.currency == "USD"
