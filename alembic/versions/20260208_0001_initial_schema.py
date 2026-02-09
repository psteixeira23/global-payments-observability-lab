"""Initial payments schema

Revision ID: 20260208_0001
Revises:
Create Date: 2026-02-08 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260208_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("customer_id", sa.String(length=128), nullable=False),
        sa.Column(
            "kyc_level",
            sa.Enum("NONE", "BASIC", "FULL", name="kyclevel", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "SUSPENDED", name="customerstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("customer_id"),
    )

    op.create_table(
        "limits_policies",
        sa.Column(
            "rail",
            sa.Enum("PIX", "BOLETO", "TED", "CARD", name="paymentmethod", native_enum=False),
            nullable=False,
            server_default="RECEIVED",
        ),
        sa.Column("min_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("max_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("daily_limit_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("velocity_limit_count", sa.Integer(), nullable=False),
        sa.Column("velocity_window_seconds", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("rail"),
    )

    op.create_table(
        "payments",
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merchant_id", sa.String(length=128), nullable=False),
        sa.Column("customer_id", sa.String(length=128), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "method",
            sa.Enum("PIX", "BOLETO", "TED", "CARD", name="paymentmethod", native_enum=False),
            nullable=False,
        ),
        sa.Column("destination", sa.String(length=128), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "RECEIVED",
                "VALIDATED",
                "IN_REVIEW",
                "PROCESSING",
                "CONFIRMED",
                "FAILED",
                "BLOCKED",
                name="paymentstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column(
            "risk_decision",
            sa.Enum("ALLOW", "REVIEW", "BLOCK", name="riskdecision", native_enum=False),
            nullable=True,
        ),
        sa.Column(
            "aml_decision",
            sa.Enum("ALLOW", "REVIEW", "BLOCK", name="amldecision", native_enum=False),
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.customer_id"]),
        sa.PrimaryKeyConstraint("payment_id"),
        sa.UniqueConstraint(
            "merchant_id", "idempotency_key", name="uq_payment_merchant_idempotency"
        ),
    )
    op.create_index("ix_payments_merchant_id", "payments", ["merchant_id"])
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"])
    op.create_index("ix_payments_account_id", "payments", ["account_id"])

    op.create_table(
        "outbox_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "PaymentRequested",
                "PaymentConfirmed",
                "PaymentFailed",
                "PaymentReviewRequired",
                name="eventtype",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "SENT", "FAILED", name="outboxstatus", native_enum=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"])
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])
    op.create_index("ix_outbox_events_next_attempt_at", "outbox_events", ["next_attempt_at"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("merchant_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_id", "idempotency_key", name="uq_idempotency_scope"),
    )
    op.create_index("ix_idempotency_records_merchant_id", "idempotency_records", ["merchant_id"])
    op.create_index("ix_idempotency_records_payment_id", "idempotency_records", ["payment_id"])


def downgrade() -> None:
    op.drop_index("ix_idempotency_records_payment_id", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_merchant_id", table_name="idempotency_records")
    op.drop_table("idempotency_records")

    op.drop_index("ix_outbox_events_next_attempt_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_status", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_type", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_id", table_name="outbox_events")
    op.drop_table("outbox_events")

    op.drop_index("ix_payments_account_id", table_name="payments")
    op.drop_index("ix_payments_customer_id", table_name="payments")
    op.drop_index("ix_payments_merchant_id", table_name="payments")
    op.drop_table("payments")

    op.drop_table("limits_policies")
    op.drop_table("customers")
