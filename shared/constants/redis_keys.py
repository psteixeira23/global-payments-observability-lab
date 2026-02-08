from __future__ import annotations

from shared.contracts import PaymentMethod, RateLimitDimension

AML_HISTORY_MAX_ITEMS = 500


def limits_policy_key(rail: PaymentMethod) -> str:
    return f"limits:policy:{rail.value}"


def limits_daily_key(date_key: str, customer_id: str, rail: PaymentMethod) -> str:
    return f"limits:daily:{date_key}:{customer_id}:{rail.value}"


def limits_velocity_key(customer_id: str, rail: PaymentMethod) -> str:
    return f"limits:velocity:{customer_id}:{rail.value}"


def rate_limit_key(dimension: RateLimitDimension, value: str, bucket: int) -> str:
    return f"rate:{dimension.value}:{value}:{bucket}"


def aml_history_key(customer_id: str) -> str:
    return f"aml:history:{customer_id}"
