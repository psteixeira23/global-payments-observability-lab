from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from shared.contracts.enums import EventType


class DomainEvent(BaseModel):
    event_id: UUID
    aggregate_id: UUID
    event_type: EventType
    occurred_at: datetime
    trace_id: str
    payload: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class PaymentRequestedPayload(BaseModel):
    payment_id: UUID
    merchant_id: str
    trace_id: str
    traceparent: str | None = None


class PaymentReviewRequiredPayload(BaseModel):
    payment_id: UUID
    merchant_id: str
    reason: str


class PaymentConfirmedPayload(BaseModel):
    payment_id: UUID
    merchant_id: str
    provider: str
    provider_reference: str


class PaymentFailedPayload(BaseModel):
    payment_id: UUID
    merchant_id: str
    provider: str
    error_category: str
    reason: str
