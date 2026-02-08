from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.contracts.enums import AmlDecision, PaymentMethod, PaymentStatus, RiskDecision


class CreatePaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    method: PaymentMethod
    destination: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class PaymentAcceptedResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    trace_id: str
    risk_decision: RiskDecision | None = None
    aml_decision: AmlDecision | None = None


class PaymentStatusResponse(BaseModel):
    payment_id: UUID
    merchant_id: str
    customer_id: str
    account_id: str
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    idempotency_key: str
    risk_score: int | None = None
    risk_decision: RiskDecision | None = None
    aml_decision: AmlDecision | None = None
    created_at: datetime
    updated_at: datetime
    last_error: str | None = None


class LimitsPolicyDTO(BaseModel):
    rail: PaymentMethod
    min_amount: Decimal
    max_amount: Decimal
    daily_limit_amount: Decimal
    velocity_limit_count: int
    velocity_window_seconds: int


class ProviderRequest(BaseModel):
    payment_id: UUID
    merchant_id: str
    amount: Decimal
    currency: str
    method: PaymentMethod


class ProviderResponse(BaseModel):
    provider_reference: str
    confirmed: bool
    provider: str
    duplicate: bool = False
    partial_failure: bool = False

    model_config = ConfigDict(extra="forbid")
