from __future__ import annotations

from dataclasses import dataclass

from shared.contracts.enums import ErrorCategory, RateLimitDimension


@dataclass
class AppError(Exception):
    category: ErrorCategory
    message: str
    http_status: int = 400


class ValidationAppError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCategory.VALIDATION_ERROR, message, http_status=422)


class IdempotencyConflictError(AppError):
    def __init__(self, message: str = "Idempotency key conflict") -> None:
        super().__init__(ErrorCategory.IDEMPOTENCY_CONFLICT, message, http_status=409)


class ConcurrencyConflictError(AppError):
    def __init__(self, message: str = "Concurrent update conflict") -> None:
        super().__init__(ErrorCategory.CONCURRENCY_CONFLICT, message, http_status=409)


class KycDeniedError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCategory.KYC_DENIED, message, http_status=403)


class LimitExceededError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCategory.LIMIT_EXCEEDED, message, http_status=422)


class RateLimitedError(AppError):
    def __init__(
        self, message: str, *, dimension: RateLimitDimension = RateLimitDimension.UNKNOWN
    ) -> None:
        self.dimension = dimension
        super().__init__(ErrorCategory.RATE_LIMITED, message, http_status=429)
