from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payments_api.services.aml_service import AmlRuleEngine
from payments_api.services.idempotency_service import IdempotencyService
from payments_api.services.limits_service import LimitsService
from payments_api.services.rate_limiter_service import RateLimiterService
from payments_api.services.risk_service import RiskScoreService
from payments_api.use_cases.create_payment import CreatePaymentUseCase
from payments_api.use_cases.get_payment import GetPaymentUseCase
from payments_api.use_cases.review_payment import (
    ApproveReviewPaymentUseCase,
    RejectReviewPaymentUseCase,
)


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory


def get_redis_client(request: Request) -> Redis:
    return request.app.state.redis_client


def get_create_payment_use_case(
    request: Request,
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> CreatePaymentUseCase:
    settings = request.app.state.settings
    idempotency_service = IdempotencyService(redis_client, settings.idempotency_ttl_seconds)
    rate_limiter = RateLimiterService(
        redis_client,
        merchant_limit=settings.merchant_rate_limit,
        customer_limit=settings.customer_rate_limit,
        account_limit=settings.account_rate_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )
    limits_service = LimitsService(redis_client, settings.limits_policy_cache_ttl_seconds)
    risk_service = RiskScoreService(settings.risk_review_threshold, settings.risk_block_threshold)
    aml_engine = AmlRuleEngine(
        redis_client,
        blocklist_destinations=settings.aml_blocklist_destinations,
        total_window_seconds=settings.aml_total_window_seconds,
        total_threshold_amount=Decimal(str(settings.aml_total_threshold_amount)),
        structuring_window_seconds=settings.aml_structuring_window_seconds,
        structuring_count_threshold=settings.aml_structuring_count_threshold,
    )
    return CreatePaymentUseCase(
        session_factory,
        idempotency_service,
        rate_limiter,
        limits_service,
        risk_service,
        aml_engine,
        settings,
    )


def get_get_payment_use_case(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> GetPaymentUseCase:
    return GetPaymentUseCase(session_factory)


def get_approve_review_use_case(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> ApproveReviewPaymentUseCase:
    return ApproveReviewPaymentUseCase(session_factory)


def get_reject_review_use_case(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> RejectReviewPaymentUseCase:
    return RejectReviewPaymentUseCase(session_factory)
