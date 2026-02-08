from __future__ import annotations

import random


def exponential_backoff(
    attempt: int, base_seconds: float = 0.05, cap_seconds: float = 2.0, jitter: float = 0.25
) -> float:
    raw = min(cap_seconds, base_seconds * (2 ** max(0, attempt - 1)))
    spread = raw * jitter
    return max(0.0, raw + random.uniform(-spread, spread))
