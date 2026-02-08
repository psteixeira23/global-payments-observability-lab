from __future__ import annotations

from payments_processor.repositories.payment_repository import PaymentRepository
from shared.contracts import PaymentORM


class MarkProcessingCommand:
    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    async def execute(self, payment: PaymentORM) -> bool:
        return await self._repository.mark_processing(payment)
