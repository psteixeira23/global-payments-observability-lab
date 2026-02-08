from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payments_api.core.errors import ValidationAppError
from payments_api.core.metrics import review_queue_size
from payments_api.repositories.outbox_repository import OutboxRepository
from payments_api.repositories.payment_repository import PaymentRepository
from shared.contracts import (
    EventType,
    PaymentAcceptedResponse,
    PaymentFailureReason,
    PaymentORM,
    PaymentRequestedPayload,
    PaymentStatus,
)
from shared.observability import current_trace_id, current_traceparent


class BaseReviewPaymentUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def _load_review_payment_or_raise(
        self, payments: PaymentRepository, payment_id: UUID
    ) -> PaymentORM:
        payment = await payments.get_by_payment_id(payment_id)
        if not payment:
            raise ValidationAppError("Payment not found")
        if payment.status != PaymentStatus.IN_REVIEW:
            raise ValidationAppError("Payment is not in review")
        return payment

    async def _record_review_queue_size(self, payments: PaymentRepository) -> None:
        queue_size = await payments.count_in_review()
        review_queue_size.record(queue_size)

    def _build_review_response(
        self,
        payment_id: UUID,
        status: PaymentStatus,
        payment: PaymentORM,
    ) -> PaymentAcceptedResponse:
        return PaymentAcceptedResponse(
            payment_id=payment_id,
            status=status,
            trace_id=current_trace_id(),
            risk_decision=payment.risk_decision,
            aml_decision=payment.aml_decision,
        )


class ApproveReviewPaymentUseCase(BaseReviewPaymentUseCase):
    async def execute(self, payment_id: UUID) -> PaymentAcceptedResponse:
        async with self._session_factory() as session:
            payments = PaymentRepository(session)
            payment = await self._load_review_payment_or_raise(payments, payment_id)

            await payments.update_status(payment_id, PaymentStatus.RECEIVED)
            outbox = OutboxRepository(session)
            self._enqueue_payment_requested(outbox, payment_id, payment.merchant_id)
            await session.commit()
            await self._record_review_queue_size(payments)
            return self._build_review_response(payment_id, PaymentStatus.RECEIVED, payment)

    def _enqueue_payment_requested(
        self, outbox: OutboxRepository, payment_id: UUID, merchant_id: str
    ) -> None:
        payload = PaymentRequestedPayload(
            payment_id=payment_id,
            merchant_id=merchant_id,
            trace_id=current_trace_id(),
            traceparent=current_traceparent(),
        ).model_dump(mode="json")
        outbox.add_event(
            aggregate_id=payment_id,
            event_type=EventType.PAYMENT_REQUESTED,
            payload=payload,
        )


class RejectReviewPaymentUseCase(BaseReviewPaymentUseCase):
    async def execute(self, payment_id: UUID) -> PaymentAcceptedResponse:
        async with self._session_factory() as session:
            payments = PaymentRepository(session)
            payment = await self._load_review_payment_or_raise(payments, payment_id)

            await payments.update_status(
                payment_id,
                PaymentStatus.BLOCKED,
                last_error=PaymentFailureReason.MANUAL_REVIEW_REJECTED.value,
            )
            await session.commit()
            await self._record_review_queue_size(payments)
            return self._build_review_response(payment_id, PaymentStatus.BLOCKED, payment)
