from __future__ import annotations

import pytest

from shared.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)


def test_circuit_breaker_opens_after_threshold() -> None:
    breaker = CircuitBreaker(
        CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=999)
    )

    breaker.on_failure()
    breaker.on_failure()

    assert breaker.state == "open"
    with pytest.raises(CircuitBreakerOpenError):
        breaker.allow_call()


def test_circuit_breaker_moves_to_half_open_and_closes_on_success() -> None:
    breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=0))

    breaker.on_failure()

    assert breaker.state == "half_open"
    breaker.on_success()
    assert breaker.state == "closed"
