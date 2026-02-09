from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from payments_api.api.dependencies import (
    enforce_api_auth,
    get_approve_review_use_case,
    get_create_payment_use_case,
    get_get_payment_use_case,
    get_reject_review_use_case,
)
from payments_api.use_cases.create_payment import CreatePaymentUseCase
from payments_api.use_cases.get_payment import GetPaymentUseCase
from payments_api.use_cases.review_payment import (
    ApproveReviewPaymentUseCase,
    RejectReviewPaymentUseCase,
)
from shared.contracts import CreatePaymentRequest, PaymentAcceptedResponse, PaymentStatusResponse

router = APIRouter(tags=["payments"], dependencies=[Depends(enforce_api_auth)])


@router.post("/payments", status_code=status.HTTP_202_ACCEPTED)
async def create_payment(
    payload: CreatePaymentRequest,
    use_case: Annotated[CreatePaymentUseCase, Depends(get_create_payment_use_case)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    merchant_id: Annotated[str, Header(alias="X-Merchant-Id")],
    customer_id: Annotated[str, Header(alias="X-Customer-Id")],
    account_id: Annotated[str, Header(alias="X-Account-Id")],
) -> PaymentAcceptedResponse:
    headers = {
        "Idempotency-Key": idempotency_key,
        "X-Merchant-Id": merchant_id,
        "X-Customer-Id": customer_id,
        "X-Account-Id": account_id,
        "X-Rail": payload.method.value,
    }
    return await use_case.execute(payload, headers)


@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: UUID,
    use_case: Annotated[GetPaymentUseCase, Depends(get_get_payment_use_case)],
) -> PaymentStatusResponse:
    return await use_case.execute(payment_id)


@router.post("/review/{payment_id}/approve")
async def approve_review(
    payment_id: UUID,
    use_case: Annotated[ApproveReviewPaymentUseCase, Depends(get_approve_review_use_case)],
) -> PaymentAcceptedResponse:
    return await use_case.execute(payment_id)


@router.post("/review/{payment_id}/reject")
async def reject_review(
    payment_id: UUID,
    use_case: Annotated[RejectReviewPaymentUseCase, Depends(get_reject_review_use_case)],
) -> PaymentAcceptedResponse:
    return await use_case.execute(payment_id)
