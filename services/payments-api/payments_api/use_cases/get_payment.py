from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payments_api.core.errors import ValidationAppError
from payments_api.repositories.payment_repository import PaymentRepository
from shared.contracts import PaymentStatusResponse


class GetPaymentUseCase:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def execute(self, payment_id: UUID) -> PaymentStatusResponse:
        async with self._session_factory() as session:
            repository = PaymentRepository(session)
            payment = await repository.get_by_payment_id(payment_id)
            if not payment:
                raise ValidationAppError("Payment not found")
            return PaymentStatusResponse(
                payment_id=payment.payment_id,
                merchant_id=payment.merchant_id,
                customer_id=payment.customer_id,
                account_id=payment.account_id,
                amount=payment.amount,
                currency=payment.currency,
                method=payment.method,
                status=payment.status,
                idempotency_key=payment.idempotency_key,
                risk_score=payment.risk_score,
                risk_decision=payment.risk_decision,
                aml_decision=payment.aml_decision,
                created_at=payment.created_at,
                updated_at=payment.updated_at,
                last_error=payment.last_error,
            )
