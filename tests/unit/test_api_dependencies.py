from __future__ import annotations

from types import SimpleNamespace

from payments_api.api import dependencies
from payments_api.core.config import Settings
from payments_api.services.aml_service import AmlRuleEngine
from payments_api.services.limits_service import LimitsService
from payments_api.services.rate_limiter_service import RateLimiterService
from payments_api.services.risk_service import RiskScoreService
from payments_api.use_cases.create_payment import CreatePaymentUseCase
from payments_api.use_cases.get_payment import GetPaymentUseCase
from payments_api.use_cases.review_payment import (
    ApproveReviewPaymentUseCase,
    RejectReviewPaymentUseCase,
)


def _build_request() -> SimpleNamespace:
    settings = Settings(
        merchant_rate_limit=9,
        customer_rate_limit=7,
        account_rate_limit=5,
        rate_limit_window_seconds=30,
        limits_policy_cache_ttl_seconds=123,
        risk_review_threshold=55,
        risk_block_threshold=85,
        aml_total_window_seconds=700,
        aml_total_threshold_amount=4321,
        aml_structuring_window_seconds=800,
        aml_structuring_count_threshold=4,
        aml_blocklist_destinations_csv="dest-a,dest-b",
    )
    state = SimpleNamespace(
        session_factory=object(),
        redis_client=object(),
        settings=settings,
    )
    return SimpleNamespace(app=SimpleNamespace(state=state))


def test_dependency_accessors_read_from_request_state() -> None:
    request = _build_request()
    assert dependencies.get_session_factory(request) is request.app.state.session_factory
    assert dependencies.get_redis_client(request) is request.app.state.redis_client


def test_create_payment_use_case_dependency_wiring_respects_settings() -> None:
    request = _build_request()
    use_case = dependencies.get_create_payment_use_case(
        request,
        request.app.state.session_factory,
        request.app.state.redis_client,
    )

    assert isinstance(use_case, CreatePaymentUseCase)
    assert use_case._session_factory is request.app.state.session_factory  # type: ignore[attr-defined]

    rate_limiter = use_case._rate_limiter  # type: ignore[attr-defined]
    assert isinstance(rate_limiter, RateLimiterService)
    assert rate_limiter._merchant_limit == 9  # type: ignore[attr-defined]
    assert rate_limiter._customer_limit == 7  # type: ignore[attr-defined]
    assert rate_limiter._account_limit == 5  # type: ignore[attr-defined]
    assert rate_limiter._window_seconds == 30  # type: ignore[attr-defined]

    limits_service = use_case._limits_service  # type: ignore[attr-defined]
    assert isinstance(limits_service, LimitsService)
    assert limits_service._cache_ttl_seconds == 123  # type: ignore[attr-defined]

    risk_service = use_case._risk_service  # type: ignore[attr-defined]
    assert isinstance(risk_service, RiskScoreService)
    assert risk_service._review_threshold == 55  # type: ignore[attr-defined]
    assert risk_service._block_threshold == 85  # type: ignore[attr-defined]

    aml_engine = use_case._aml_engine  # type: ignore[attr-defined]
    assert isinstance(aml_engine, AmlRuleEngine)
    assert aml_engine._total_window_seconds == 700  # type: ignore[attr-defined]
    assert aml_engine._structuring_window_seconds == 800  # type: ignore[attr-defined]
    assert aml_engine._structuring_count_threshold == 4  # type: ignore[attr-defined]
    assert aml_engine._blocklist_destinations == {"dest-a", "dest-b"}  # type: ignore[attr-defined]


def test_other_use_case_dependency_factories_return_expected_types() -> None:
    request = _build_request()
    session_factory = request.app.state.session_factory
    assert isinstance(dependencies.get_get_payment_use_case(session_factory), GetPaymentUseCase)
    assert isinstance(
        dependencies.get_approve_review_use_case(session_factory), ApproveReviewPaymentUseCase
    )
    assert isinstance(
        dependencies.get_reject_review_use_case(session_factory), RejectReviewPaymentUseCase
    )
