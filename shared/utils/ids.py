from __future__ import annotations

from uuid import UUID, uuid4


def new_uuid() -> UUID:
    return uuid4()


def idempotency_scoped_key(merchant_id: str, idempotency_key: str) -> str:
    return f"{merchant_id}:{idempotency_key}"
