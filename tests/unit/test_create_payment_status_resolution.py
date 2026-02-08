from __future__ import annotations

import pytest
from payments_api.use_cases.create_payment import _resolve_status_from_decisions

from shared.contracts import AmlDecision, PaymentStatus, RiskDecision


@pytest.mark.parametrize(
    ("risk_decision", "aml_decision", "expected_status"),
    [
        (RiskDecision.BLOCK, AmlDecision.ALLOW, PaymentStatus.BLOCKED),
        (RiskDecision.ALLOW, AmlDecision.BLOCK, PaymentStatus.BLOCKED),
        (RiskDecision.REVIEW, AmlDecision.ALLOW, PaymentStatus.IN_REVIEW),
        (RiskDecision.ALLOW, AmlDecision.REVIEW, PaymentStatus.IN_REVIEW),
        (RiskDecision.ALLOW, AmlDecision.ALLOW, PaymentStatus.RECEIVED),
    ],
)
def test_resolve_status_from_decisions_maps_to_expected_status(
    risk_decision: RiskDecision,
    aml_decision: AmlDecision,
    expected_status: PaymentStatus,
) -> None:
    status = _resolve_status_from_decisions(risk_decision, aml_decision)
    assert status == expected_status
