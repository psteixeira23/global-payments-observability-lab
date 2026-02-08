# Design Patterns Map

## Strategy
- `services/payments-processor/payments_processor/providers/strategy.py`
- `services/payments-api/payments_api/services/risk_service.py`
- Provider path and risk scoring rules are both strategy-driven.

## Factory
- `services/payments-processor/payments_processor/providers/factory.py`
- Builds provider HTTP adapters from config.

## Repository
- `services/payments-api/payments_api/repositories/*.py`
- `services/payments-processor/payments_processor/repositories/*.py`
- Isolates persistence concerns from use-cases.

## Outbox Pattern
- `services/payments-api/payments_api/use_cases/create_payment.py`
- Payment state and domain events are persisted transactionally.

## Idempotency Key Pattern
- `services/payments-api/payments_api/services/idempotency_service.py`
- `services/payments-api/payments_api/repositories/idempotency_repository.py`
- Redis `SET NX` gate plus Postgres scoped snapshot fallback.

## Circuit Breaker
- `shared/resilience/circuit_breaker.py`
- Explicit state machine with half-open behavior.

## Retry + Exponential Backoff + Jitter
- `shared/resilience/retry.py`
- `shared/resilience/backoff.py`

## Bulkhead
- `shared/resilience/bulkhead.py`

## Adapter
- `services/payments-processor/payments_processor/providers/adapter.py`
- HTTP provider wrapper abstraction.

## Command
- `services/payments-processor/payments_processor/commands/*.py`
- Discrete worker actions for orchestration.
