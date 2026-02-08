from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from opentelemetry import trace
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payments_api.core.config import Settings
from payments_api.core.errors import (
    IdempotencyConflictError,
    KycDeniedError,
    LimitExceededError,
    RateLimitedError,
    ValidationAppError,
)
from payments_api.core.metrics import (
    aml_decisions_total,
    idempotency_replay_total,
    kyc_check_duration,
    kyc_denied_total,
    limits_check_duration,
    limits_exceeded_total,
    rate_limited_total,
    review_queue_size,
    risk_decisions_total,
)
from payments_api.repositories.customer_repository import CustomerRepository
from payments_api.repositories.idempotency_repository import IdempotencyRepository
from payments_api.repositories.limits_policy_repository import LimitsPolicyRepository
from payments_api.repositories.outbox_repository import OutboxRepository
from payments_api.repositories.payment_repository import PaymentCreateData, PaymentRepository
from payments_api.services.aml_service import AmlRuleEngine
from payments_api.services.idempotency_service import IdempotencyService
from payments_api.services.kyc_service import KycService
from payments_api.services.limits_service import LimitsEvaluation, LimitsService
from payments_api.services.rate_limiter_service import RateLimiterService
from payments_api.services.risk_service import RiskScoreService
from shared.contracts import (
    AmlDecision,
    CreatePaymentRequest,
    CustomerORM,
    EventType,
    PaymentAcceptedResponse,
    PaymentMethod,
    PaymentORM,
    PaymentRequestedPayload,
    PaymentReviewRequiredPayload,
    PaymentStatus,
    ReviewReason,
    RiskDecision,
)
from shared.logging import get_logger, update_correlation_context
from shared.logging.fields import (
    ACCOUNT_ID,
    AML_DECISION,
    CUSTOMER_ID,
    DESTINATION,
    PAYMENT_ID,
    RAIL,
    RISK_DECISION,
    STATUS,
)
from shared.observability import current_trace_id, current_traceparent
from shared.utils.ids import new_uuid
from shared.utils.validation import ensure_supported_currency, require_header

logger = get_logger(__name__)


@dataclass(frozen=True)
class RequestContext:
    merchant_id: str
    customer_id: str
    account_id: str
    idempotency_key: str


@dataclass(frozen=True)
class ControlDecision:
    risk_score: int
    risk_decision: RiskDecision
    aml_decision: AmlDecision
    final_status: PaymentStatus


@dataclass(frozen=True)
class RepositoryBundle:
    payment: PaymentRepository
    outbox: OutboxRepository
    customer: CustomerRepository
    limits: LimitsPolicyRepository
    idempotency: IdempotencyRepository


class DurationMetric(Protocol):
    def record(self, amount: float, attributes: dict[str, str]) -> None: ...


class CreatePaymentUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        idempotency_service: IdempotencyService,
        rate_limiter: RateLimiterService,
        limits_service: LimitsService,
        risk_service: RiskScoreService,
        aml_engine: AmlRuleEngine,
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._idempotency_service = idempotency_service
        self._rate_limiter = rate_limiter
        self._limits_service = limits_service
        self._risk_service = risk_service
        self._aml_engine = aml_engine
        self._settings = settings
        self._kyc_service = KycService()
        self._tracer = trace.get_tracer(__name__)

    async def execute(
        self, request: CreatePaymentRequest, headers: dict[str, str]
    ) -> PaymentAcceptedResponse:
        request_context = self._build_request_context(headers, request)
        async with self._session_factory() as session:
            repositories = self._build_repositories(session)

            replayed = await self._try_return_replayed_response(repositories, request_context)
            if replayed:
                return replayed

            if not await self._acquire_idempotency_lock(request_context):
                return await self._resolve_pending_idempotent_request(repositories, request_context)

            return await self._create_payment_with_controls(
                session,
                repositories,
                request_context,
                request,
            )

    def _build_request_context(
        self, headers: dict[str, str], request: CreatePaymentRequest
    ) -> RequestContext:
        with self._tracer.start_as_current_span("validate"):
            merchant_id = require_header(headers, "X-Merchant-Id")
            customer_id = require_header(headers, "X-Customer-Id")
            account_id = require_header(headers, "X-Account-Id")
            idempotency_key = require_header(headers, "Idempotency-Key")
            request.currency = self._normalize_currency(request.currency)
            update_correlation_context(
                {CUSTOMER_ID: customer_id, ACCOUNT_ID: account_id, RAIL: request.method.value}
            )
            return RequestContext(
                merchant_id=merchant_id,
                customer_id=customer_id,
                account_id=account_id,
                idempotency_key=idempotency_key,
            )

    def _normalize_currency(self, currency: str) -> str:
        try:
            return ensure_supported_currency(currency, self._settings.supported_currencies)
        except ValueError as exc:
            raise ValidationAppError(str(exc)) from exc

    async def _acquire_idempotency_lock(self, request_context: RequestContext) -> bool:
        return await self._idempotency_service.acquire(
            request_context.merchant_id,
            request_context.idempotency_key,
        )

    async def _create_payment_with_controls(
        self,
        session: AsyncSession,
        repositories: RepositoryBundle,
        request_context: RequestContext,
        request: CreatePaymentRequest,
    ) -> PaymentAcceptedResponse:
        customer = await self._load_customer_or_raise(
            repositories.customer, request_context.customer_id
        )
        limits_evaluation = await self._run_pre_checks(
            repositories, request_context, request, customer
        )
        control_decision = await self._evaluate_controls(
            repositories,
            customer,
            request,
            limits_evaluation,
            request_context.customer_id,
        )
        response = self._build_response_payload(control_decision)
        self._update_decision_correlation_fields(control_decision)

        replayed = await self._persist_payment_transaction(
            session,
            repositories,
            request_context,
            request,
            control_decision,
            response,
        )
        if replayed:
            return replayed

        await self._after_commit_observability(
            repositories.payment,
            request_context,
            request,
            response,
            control_decision,
        )
        return response

    async def _run_pre_checks(
        self,
        repositories: RepositoryBundle,
        request_context: RequestContext,
        request: CreatePaymentRequest,
        customer: CustomerORM,
    ) -> LimitsEvaluation:
        self._enforce_kyc(customer, request.method)
        limits_evaluation = await self._enforce_limits(
            repositories.payment,
            repositories.limits,
            request_context.customer_id,
            request,
        )
        await self._enforce_rate_limit(request_context)
        return limits_evaluation

    def _update_decision_correlation_fields(self, control_decision: ControlDecision) -> None:
        update_correlation_context(
            {
                RISK_DECISION: control_decision.risk_decision.value,
                AML_DECISION: control_decision.aml_decision.value,
            }
        )

    async def _load_customer_or_raise(
        self, repository: CustomerRepository, customer_id: str
    ) -> CustomerORM:
        customer = await repository.get_by_id(customer_id)
        if customer is None:
            raise ValidationAppError("Customer not found")
        return customer

    def _enforce_kyc(self, customer: CustomerORM, method: PaymentMethod) -> None:
        rail_attributes = self._rail_attributes(method)
        try:
            with self._timed_span("kyc_check", kyc_check_duration, rail_attributes):
                self._kyc_service.enforce(customer, method)
        except KycDeniedError:
            kyc_denied_total.add(1, rail_attributes)
            raise

    async def _enforce_limits(
        self,
        payment_repository: PaymentRepository,
        limits_repository: LimitsPolicyRepository,
        customer_id: str,
        request: CreatePaymentRequest,
    ) -> LimitsEvaluation:
        rail_attributes = self._rail_attributes(request.method)
        try:
            with self._timed_span("limits_check", limits_check_duration, rail_attributes):
                return await self._limits_service.enforce(
                    payment_repository,
                    limits_repository,
                    customer_id=customer_id,
                    rail=request.method,
                    amount=request.amount,
                )
        except LimitExceededError:
            limits_exceeded_total.add(1, rail_attributes)
            raise

    async def _enforce_rate_limit(self, request_context: RequestContext) -> None:
        with self._tracer.start_as_current_span("rate_limit_check"):
            try:
                await self._rate_limiter.enforce(
                    request_context.merchant_id,
                    request_context.customer_id,
                    request_context.account_id,
                )
            except RateLimitedError as exc:
                rate_limited_total.add(1, {"dimension": exc.dimension.value})
                raise

    @contextmanager
    def _timed_span(
        self,
        span_name: str,
        duration_metric: DurationMetric,
        attributes: dict[str, str],
    ) -> Iterator[None]:
        start_time = time.perf_counter()
        with self._tracer.start_as_current_span(span_name):
            try:
                yield
            finally:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                duration_metric.record(elapsed_ms, attributes)

    def _rail_attributes(self, method: PaymentMethod) -> dict[str, str]:
        return {"rail": method.value}

    async def _evaluate_controls(
        self,
        repositories: RepositoryBundle,
        customer: CustomerORM,
        request: CreatePaymentRequest,
        limits_evaluation: LimitsEvaluation,
        customer_id: str,
    ) -> ControlDecision:
        risk_score, risk_decision = await self._evaluate_risk(
            repositories.payment,
            customer,
            request,
            limits_evaluation,
        )
        aml_decision = await self._evaluate_aml(
            repositories.payment,
            customer_id,
            request,
            limits_evaluation,
        )
        risk_decisions_total.add(1, {"decision": risk_decision.value})
        aml_decisions_total.add(1, {"decision": aml_decision.value})

        return ControlDecision(
            risk_score=risk_score,
            risk_decision=risk_decision,
            aml_decision=aml_decision,
            final_status=_resolve_status_from_decisions(risk_decision, aml_decision),
        )

    async def _evaluate_risk(
        self,
        payment_repository: PaymentRepository,
        customer: CustomerORM,
        request: CreatePaymentRequest,
        limits_evaluation: LimitsEvaluation,
    ) -> tuple[int, RiskDecision]:
        with self._tracer.start_as_current_span("risk_score"):
            return await self._risk_service.evaluate(
                payment_repository,
                customer=customer,
                amount=request.amount,
                policy=limits_evaluation.policy,
                velocity_count=limits_evaluation.velocity_count,
                destination=request.destination,
            )

    async def _evaluate_aml(
        self,
        payment_repository: PaymentRepository,
        customer_id: str,
        request: CreatePaymentRequest,
        limits_evaluation: LimitsEvaluation,
    ) -> AmlDecision:
        with self._tracer.start_as_current_span("aml_check"):
            return await self._aml_engine.evaluate(
                payment_repository,
                customer_id=customer_id,
                rail=request.method,
                amount=request.amount,
                destination=request.destination,
                policy=limits_evaluation.policy,
            )

    def _build_response_payload(self, control_decision: ControlDecision) -> PaymentAcceptedResponse:
        return self._build_payment_response(
            payment_id=new_uuid(),
            status=control_decision.final_status,
            risk_decision=control_decision.risk_decision,
            aml_decision=control_decision.aml_decision,
        )

    async def _persist_payment_transaction(
        self,
        session: AsyncSession,
        repositories: RepositoryBundle,
        request_context: RequestContext,
        request: CreatePaymentRequest,
        control_decision: ControlDecision,
        response_payload: PaymentAcceptedResponse,
    ) -> PaymentAcceptedResponse | None:
        try:
            self._persist_payment_and_outbox(
                repositories,
                request_context,
                request,
                control_decision,
                response_payload,
            )
            repositories.idempotency.create_snapshot(
                merchant_id=request_context.merchant_id,
                idempotency_key=request_context.idempotency_key,
                payment_id=response_payload.payment_id,
                status_code=202,
                response_payload=response_payload.model_dump(mode="json"),
            )
            await session.commit()
            return None
        except IntegrityError:
            await session.rollback()
            replayed_response = await self._resolve_replayed_after_conflict(
                repositories, request_context
            )
            if replayed_response:
                return replayed_response
            raise IdempotencyConflictError() from None

    async def _resolve_replayed_after_conflict(
        self,
        repositories: RepositoryBundle,
        request_context: RequestContext,
    ) -> PaymentAcceptedResponse | None:
        replayed_response = await self._try_return_replayed_response(repositories, request_context)
        if replayed_response:
            return replayed_response

        existing = await repositories.payment.get_by_merchant_and_idempotency(
            request_context.merchant_id,
            request_context.idempotency_key,
        )
        if not existing:
            return None
        return self._build_response_from_existing_payment(existing)

    def _persist_payment_and_outbox(
        self,
        repositories: RepositoryBundle,
        request_context: RequestContext,
        request: CreatePaymentRequest,
        control_decision: ControlDecision,
        response_payload: PaymentAcceptedResponse,
    ) -> None:
        repositories.payment.create_payment(
            PaymentCreateData(
                payment_id=response_payload.payment_id,
                merchant_id=request_context.merchant_id,
                customer_id=request_context.customer_id,
                account_id=request_context.account_id,
                amount=request.amount,
                currency=request.currency,
                method=request.method,
                destination=request.destination,
                status=response_payload.status,
                idempotency_key=request_context.idempotency_key,
                risk_score=control_decision.risk_score,
                risk_decision=control_decision.risk_decision,
                aml_decision=control_decision.aml_decision,
                metadata=request.metadata,
            )
        )
        self._persist_outbox_events(repositories.outbox, request_context, response_payload)

    def _persist_outbox_events(
        self,
        outbox_repository: OutboxRepository,
        request_context: RequestContext,
        response_payload: PaymentAcceptedResponse,
    ) -> None:
        if response_payload.status == PaymentStatus.RECEIVED:
            payload = PaymentRequestedPayload(
                payment_id=response_payload.payment_id,
                merchant_id=request_context.merchant_id,
                trace_id=current_trace_id(),
                traceparent=current_traceparent(),
            ).model_dump(mode="json")
            outbox_repository.add_event(
                aggregate_id=response_payload.payment_id,
                event_type=EventType.PAYMENT_REQUESTED,
                payload=payload,
            )
            return

        if response_payload.status == PaymentStatus.IN_REVIEW:
            review_payload = PaymentReviewRequiredPayload(
                payment_id=response_payload.payment_id,
                merchant_id=request_context.merchant_id,
                reason=ReviewReason.RISK_OR_AML_REVIEW.value,
            ).model_dump(mode="json")
            outbox_repository.add_event(
                aggregate_id=response_payload.payment_id,
                event_type=EventType.PAYMENT_REVIEW_REQUIRED,
                payload=review_payload,
            )

    async def _after_commit_observability(
        self,
        payment_repository: PaymentRepository,
        request_context: RequestContext,
        request: CreatePaymentRequest,
        response_payload: PaymentAcceptedResponse,
        control_decision: ControlDecision,
    ) -> None:
        if response_payload.status != PaymentStatus.BLOCKED:
            await self._aml_engine.record_outgoing(
                customer_id=request_context.customer_id,
                rail=request.method,
                amount=request.amount,
            )

        queue_size = await payment_repository.count_in_review()
        review_queue_size.record(queue_size)
        logger.info(
            "payment_created",
            extra={
                "extra_fields": {
                    PAYMENT_ID: str(response_payload.payment_id),
                    STATUS: response_payload.status.value,
                    RISK_DECISION: control_decision.risk_decision.value,
                    AML_DECISION: control_decision.aml_decision.value,
                    DESTINATION: request.destination,
                }
            },
        )

    async def _try_return_replayed_response(
        self,
        repositories: RepositoryBundle,
        request_context: RequestContext,
    ) -> PaymentAcceptedResponse | None:
        snapshot = await repositories.idempotency.get_snapshot(
            request_context.merchant_id,
            request_context.idempotency_key,
        )
        if not snapshot:
            return None
        idempotency_replay_total.add(1)
        return PaymentAcceptedResponse.model_validate(snapshot.response_payload)

    async def _resolve_pending_idempotent_request(
        self,
        repositories: RepositoryBundle,
        request_context: RequestContext,
    ) -> PaymentAcceptedResponse:
        for _ in range(5):
            replayed_response = await self._try_return_replayed_response(
                repositories, request_context
            )
            if replayed_response:
                return replayed_response

            existing_payment = await repositories.payment.get_by_merchant_and_idempotency(
                request_context.merchant_id,
                request_context.idempotency_key,
            )
            if existing_payment:
                return self._build_response_from_existing_payment(existing_payment)
            await asyncio.sleep(0.02)
        raise IdempotencyConflictError()

    def _build_response_from_existing_payment(self, payment: PaymentORM) -> PaymentAcceptedResponse:
        return self._build_payment_response(
            payment_id=payment.payment_id,
            status=payment.status,
            risk_decision=payment.risk_decision,
            aml_decision=payment.aml_decision,
        )

    def _build_payment_response(
        self,
        *,
        payment_id: UUID,
        status: PaymentStatus,
        risk_decision: RiskDecision | None,
        aml_decision: AmlDecision | None,
    ) -> PaymentAcceptedResponse:
        return PaymentAcceptedResponse(
            payment_id=payment_id,
            status=status,
            trace_id=current_trace_id(),
            risk_decision=risk_decision,
            aml_decision=aml_decision,
        )

    def _build_repositories(self, session: AsyncSession) -> RepositoryBundle:
        return RepositoryBundle(
            payment=PaymentRepository(session),
            outbox=OutboxRepository(session),
            customer=CustomerRepository(session),
            limits=LimitsPolicyRepository(session),
            idempotency=IdempotencyRepository(session),
        )

    def _build_repository_bundle(self, session: AsyncSession) -> RepositoryBundle:
        return self._build_repositories(session)


def _resolve_status_from_decisions(
    risk_decision: RiskDecision, aml_decision: AmlDecision
) -> PaymentStatus:
    if risk_decision == RiskDecision.BLOCK or aml_decision == AmlDecision.BLOCK:
        return PaymentStatus.BLOCKED
    if risk_decision == RiskDecision.REVIEW or aml_decision == AmlDecision.REVIEW:
        return PaymentStatus.IN_REVIEW
    return PaymentStatus.RECEIVED
