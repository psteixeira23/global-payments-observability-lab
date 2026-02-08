# Architecture and Design Patterns

## Current Architecture

The lab uses **Layered + Ports and Adapters** in a monorepo:

- Domain and application rules live in use-cases/services/commands.
- Interface layer is isolated in FastAPI routes.
- Infrastructure concerns (SQLAlchemy, Redis, HTTP adapters) are isolated in repositories/adapters.
- Shared contracts/observability/resilience code lives under `shared/`.

This fit is intentional for a local-first fintech simulation:

- keeps business flow deterministic and testable;
- allows realistic failure injection;
- keeps infra-replacement cost low (mock provider -> real provider, outbox polling -> queue).

## Pattern Map (with Code References)

### Strategy

- `services/payments-processor/payments_processor/providers/strategy.py`
- `services/payments-api/payments_api/services/risk_service.py`

Usage:

- provider path/selection by payment method;
- risk scoring by composable rule strategies.

### Factory

- `services/payments-processor/payments_processor/providers/factory.py`

Usage:

- builds provider clients from runtime configuration.

### Repository

- `services/payments-api/payments_api/repositories/*.py`
- `services/payments-processor/payments_processor/repositories/*.py`

Usage:

- isolates SQL/persistence from use-cases and commands.

### Outbox Pattern

- `services/payments-api/payments_api/use_cases/create_payment.py`
- `services/payments-processor/payments_processor/workers/outbox_worker.py`

Usage:

- payment + event persistence in one transaction;
- async worker delivery with retries and backoff.

### Idempotency Key Pattern

- `services/payments-api/payments_api/services/idempotency_service.py`
- `services/payments-api/payments_api/repositories/idempotency_repository.py`

Usage:

- Redis `SET NX` first gate;
- persisted response snapshot scoped by `(merchant_id, idempotency_key)`.

### Adapter

- `services/payments-processor/payments_processor/providers/adapter.py`

Usage:

- normalizes provider HTTP contract and error mapping.

### Command

- `services/payments-processor/payments_processor/commands/*.py`

Usage:

- worker orchestration split into small command units.

### Retry + Backoff + Circuit Breaker + Bulkhead

- `shared/resilience/retry.py`
- `shared/resilience/backoff.py`
- `shared/resilience/circuit_breaker.py`
- `shared/resilience/bulkhead.py`
- composed in `services/payments-processor/payments_processor/commands/call_provider.py`

Usage:

- protects downstream provider calls from retry storms and cascading failures.

## Trade-offs and Alternatives

### Why this approach

- strong separation of concerns with low cognitive load;
- deterministic control pipelines (KYC, limits, AML, risk, rate limiting);
- high testability without external SaaS dependency.

### Why alternatives were not chosen in v1

- Full CQRS/Event Sourcing:
  - excellent auditability, but higher operational complexity for MVP.
- Kafka/Rabbit as first transport:
  - useful at scale, but unnecessary complexity for local deterministic baseline.
- Multi-repo split:
  - increases coordination overhead for shared contracts in an educational/lab setup.

## Observability and Resilience Composition

- HTTP edge starts request correlation and trace context.
- `payments-api` validates, applies controls, persists payment and outbox.
- `payments-processor` polls outbox, marks processing, calls provider through resilience stack, finalizes status.
- Logs and metrics are emitted in each stage with correlated fields (`trace_id`, `payment_id`, `merchant_id`, etc.).

## Extension Guide

### Add a New Provider

1. Add provider mapping in `providers/strategy.py`.
2. Expose/adjust provider endpoint in `provider-mock`.
3. Reuse `ProviderClientAdapter` contract.
4. Add provider-specific resilience thresholds if needed.
5. Add unit tests for strategy + adapter + command behavior.

### Add a New Service

1. Keep domain/application independent of framework and ORM.
2. Reuse `shared/contracts`, `shared/logging`, `shared/observability`, and `shared/resilience`.
3. Integrate via outbox-compatible events for async boundaries.
4. Add tests at use-case and adapter boundaries first.
