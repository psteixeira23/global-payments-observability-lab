from __future__ import annotations

from typing import Any
from uuid import UUID

from shared.contracts import PaymentAcceptedResponse, PaymentStatusResponse, ProviderResponse


class FakeCreatePaymentUseCase:
    def __init__(self, response: PaymentAcceptedResponse) -> None:
        self._response = response
        self.payload: Any = None
        self.headers: dict[str, str] | None = None

    async def execute(self, payload: Any, headers: dict[str, str]) -> PaymentAcceptedResponse:
        self.payload = payload
        self.headers = headers
        return self._response


class FakeGetPaymentUseCase:
    def __init__(self, response: PaymentStatusResponse) -> None:
        self._response = response
        self.payment_id: UUID | None = None

    async def execute(self, payment_id: UUID) -> PaymentStatusResponse:
        self.payment_id = payment_id
        return self._response


class FakeReviewUseCase:
    def __init__(self, response: PaymentAcceptedResponse) -> None:
        self._response = response
        self.payment_id: UUID | None = None

    async def execute(self, payment_id: UUID) -> PaymentAcceptedResponse:
        self.payment_id = payment_id
        return self._response


class FakeProviderEngine:
    def __init__(
        self,
        *,
        response: ProviderResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response
        self._error = error
        self.provider_slug: str | None = None
        self.payload: Any = None

    async def simulate(self, provider_slug: str, payload: Any) -> ProviderResponse:
        if self._error is not None:
            raise self._error
        self.provider_slug = provider_slug
        self.payload = payload
        if self._response is not None:
            return self._response
        return ProviderResponse(
            provider_reference=f"{provider_slug}-ref",
            confirmed=True,
            provider=f"{provider_slug}-provider",
            duplicate=False,
            partial_failure=False,
        )


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self) -> FakeSessionFactory:
        return self

    async def __aenter__(self) -> FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


class FakePaymentRepository:
    def __init__(self, payment: object | None) -> None:
        self.payment = payment
        self.updated: tuple[Any, ...] | None = None
        self.in_review_count = 1

    async def get_by_payment_id(self, payment_id: UUID) -> object | None:
        return self.payment

    async def update_status(
        self, payment_id: UUID, status: Any, *, last_error: str | None = None
    ) -> bool:
        self.updated = (payment_id, status, last_error)
        return True

    async def count_in_review(self) -> int:
        return self.in_review_count


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.events: list[tuple[Any, ...]] = []

    def add_event(self, *, aggregate_id: Any, event_type: Any, payload: dict[str, Any]) -> None:
        self.events.append((aggregate_id, event_type, payload))
