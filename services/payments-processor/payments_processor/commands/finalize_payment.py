from __future__ import annotations

from payments_processor.repositories.outbox_repository import OutboxRepository
from payments_processor.repositories.payment_repository import PaymentRepository
from shared.contracts import EventType, PaymentORM
from shared.contracts.events import PaymentConfirmedPayload, PaymentFailedPayload


class FinalizePaymentCommand:
    def __init__(
        self, payment_repository: PaymentRepository, outbox_repository: OutboxRepository
    ) -> None:
        self._payment_repository = payment_repository
        self._outbox_repository = outbox_repository

    async def confirm(self, payment: PaymentORM, provider: str, provider_reference: str) -> None:
        await self._payment_repository.mark_confirmed(payment)
        payload = PaymentConfirmedPayload(
            payment_id=payment.payment_id,
            merchant_id=payment.merchant_id,
            provider=provider,
            provider_reference=provider_reference,
        ).model_dump(mode="json")
        self._outbox_repository.emit_event(payment.payment_id, EventType.PAYMENT_CONFIRMED, payload)

    async def fail(self, payment: PaymentORM, provider: str, category: str, reason: str) -> None:
        await self._payment_repository.mark_failed(payment, reason)
        payload = PaymentFailedPayload(
            payment_id=payment.payment_id,
            merchant_id=payment.merchant_id,
            provider=provider,
            error_category=category,
            reason=reason,
        ).model_dump(mode="json")
        self._outbox_repository.emit_event(payment.payment_id, EventType.PAYMENT_FAILED, payload)
