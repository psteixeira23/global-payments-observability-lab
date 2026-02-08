from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum


class CircuitBreakerOpenError(RuntimeError):
    pass


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_timeout_seconds: int = 10


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: datetime | None = None

    @property
    def state(self) -> str:
        if self._state == CircuitState.OPEN and self._can_half_open():
            self._state = CircuitState.HALF_OPEN
        return self._state.value

    def allow_call(self) -> None:
        if self._state == CircuitState.OPEN and not self._can_half_open():
            raise CircuitBreakerOpenError("Circuit is open")
        if self._state == CircuitState.OPEN:
            self._state = CircuitState.HALF_OPEN

    def on_success(self) -> None:
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = None

    def on_failure(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._trip_open()
            return
        self._failures += 1
        if self._failures >= self._config.failure_threshold:
            self._trip_open()

    def _trip_open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = datetime.now(UTC)

    def _can_half_open(self) -> bool:
        if not self._opened_at:
            return False
        recover_at = self._opened_at + timedelta(seconds=self._config.recovery_timeout_seconds)
        return datetime.now(UTC) >= recover_at
