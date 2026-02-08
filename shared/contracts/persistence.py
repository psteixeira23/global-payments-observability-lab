from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.contracts.enums import (
    AmlDecision,
    CustomerStatus,
    EventType,
    KycLevel,
    OutboxStatus,
    PaymentMethod,
    PaymentStatus,
    RiskDecision,
)


class Base(DeclarativeBase):
    pass


class CustomerORM(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    kyc_level: Mapped[KycLevel] = mapped_column(
        Enum(KycLevel, native_enum=False), nullable=False, default=KycLevel.NONE
    )
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, native_enum=False), nullable=False, default=CustomerStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LimitsPolicyORM(Base):
    __tablename__ = "limits_policies"

    rail: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False), primary_key=True
    )
    min_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    max_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    daily_limit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    velocity_limit_count: Mapped[int] = mapped_column(Integer, nullable=False)
    velocity_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)


class PaymentORM(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("merchant_id", "idempotency_key", name="uq_payment_merchant_idempotency"),
    )

    payment_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    merchant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False), nullable=False
    )
    destination: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False), nullable=False, default=PaymentStatus.RECEIVED
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_decision: Mapped[RiskDecision | None] = mapped_column(
        Enum(RiskDecision, native_enum=False), nullable=True
    )
    aml_decision: Mapped[AmlDecision | None] = mapped_column(
        Enum(AmlDecision, native_enum=False), nullable=True
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class OutboxEventORM(Base):
    __tablename__ = "outbox_events"

    event_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    aggregate_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, native_enum=False),
        nullable=False,
        default=OutboxStatus.PENDING,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )


class IdempotencyRecordORM(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("merchant_id", "idempotency_key", name="uq_idempotency_scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payment_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
