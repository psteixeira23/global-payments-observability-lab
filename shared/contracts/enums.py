from __future__ import annotations

from enum import Enum


class PaymentMethod(str, Enum):
    PIX = "PIX"
    BOLETO = "BOLETO"
    TED = "TED"
    CARD = "CARD"


class PaymentStatus(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    IN_REVIEW = "IN_REVIEW"
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class OutboxStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class EventType(str, Enum):
    PAYMENT_REQUESTED = "PaymentRequested"
    PAYMENT_CONFIRMED = "PaymentConfirmed"
    PAYMENT_FAILED = "PaymentFailed"
    PAYMENT_REVIEW_REQUIRED = "PaymentReviewRequired"


class RateLimitDimension(str, Enum):
    MERCHANT = "merchant"
    CUSTOMER = "customer"
    ACCOUNT = "account"
    UNKNOWN = "unknown"


class KycLevel(str, Enum):
    NONE = "NONE"
    BASIC = "BASIC"
    FULL = "FULL"


class CustomerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class RiskDecision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class AmlDecision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class ReviewReason(str, Enum):
    RISK_OR_AML_REVIEW = "risk_or_aml_review"


class PaymentFailureReason(str, Enum):
    MANUAL_REVIEW_REJECTED = "manual_review_rejected"
    PROVIDER_PARTIAL_FAILURE = "provider_partial_failure"
    UNEXPECTED = "unexpected"


class ProviderName(str, Enum):
    UNKNOWN = "unknown"


class ErrorCategory(str, Enum):
    VALIDATION_ERROR = "validation_error"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_5XX = "provider_5xx"
    CONCURRENCY_CONFLICT = "concurrency_conflict"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    KYC_DENIED = "kyc_denied"
    LIMIT_EXCEEDED = "limit_exceeded"
    RATE_LIMITED = "rate_limited"
    AML_BLOCKED = "aml_blocked"
    RISK_BLOCKED = "risk_blocked"
