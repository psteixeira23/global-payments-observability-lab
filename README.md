# global-payments-observability-lab

Local-first engineering lab for fintech payments observability and control layers.

No external SaaS tooling is required to run this project.

## 1. What This Project Solves

Modern payment systems need deterministic controls before money movement:
- KYC and customer status checks.
- Amount, daily, and velocity limits.
- Rate limiting by merchant/customer/account.
- Deterministic risk and AML decisions.
- Idempotent edge handling with consistent replay responses.
- Correlated logs, metrics, and traces across sync API + async worker.

This repository provides a realistic baseline architecture for those controls.

## 2. Repository Architecture

Services:
- `services/payments-api`: FastAPI edge service. Validates requests, enforces controls, persists payments, writes outbox.
- `services/payments-processor`: async worker. Polls outbox, calls provider, applies resilience, updates final status.
- `services/provider-mock`: deterministic external provider simulator with configurable fault injection.

Shared package:
- `shared/contracts`: enums, DTOs, persistence models, event schemas.
- `shared/logging`: JSON structured logging + redaction + correlation middleware.
- `shared/observability`: OpenTelemetry setup and trace propagation helpers.
- `shared/resilience`: retry/backoff, circuit breaker, bulkhead.
- `shared/utils` and `shared/constants`: helper functions and key conventions.

Infrastructure:
- `infra/docker/docker-compose.yml`: Postgres + Redis + 3 services.

## 3. Prerequisites

Required:
- Docker Desktop running (not paused).
- Docker Compose v2 (`docker compose` command).
- Free local ports: `5432`, `6379`, `8080`, `8082`.

For local lint/type-check/tests (outside containers):
- Python `3.12`.
- Poetry `1.8+` (CI uses Poetry `2.1.4`).

Recommended verification:

```bash
docker --version
docker compose version
python3 --version
poetry --version
```

## 4. Quick Start (Recommended)

This path is enough for most users and does not require manual environment setup.

1. Clone and enter the project.

```bash
git clone <your-repo-url>
cd global-payments-observability-lab
```

2. Start all services.

```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
```

3. Confirm services are healthy.

```bash
docker compose -f infra/docker/docker-compose.yml ps
curl -s http://localhost:8080/health
curl -s http://localhost:8082/health
```

Expected health responses:
- `{"status":"ok"}` from `payments-api`.
- `{"status":"ok"}` from `provider-mock`.

4. Create your first payment.

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: quickstart-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":100.00,"currency":"BRL","method":"PIX","destination":"dest-safe-001"}'
```

5. Query payment status using returned `payment_id`.

```bash
curl -s http://localhost:8080/payments/<payment_id>
```

6. Stop stack when done.

```bash
docker compose -f infra/docker/docker-compose.yml down
```

To reset database/cache volumes:

```bash
docker compose -f infra/docker/docker-compose.yml down -v
```

## 5. Local Data Seeded at Startup

When `APP_ENV=local`, the API initializes schema and seeds baseline data.

Customers:
- `customer-basic-001` (`BASIC`, `ACTIVE`)
- `customer-full-001` (`FULL`, `ACTIVE`)
- `customer-suspended-001` (`FULL`, `SUSPENDED`)
- `customer-none-001` (`NONE`, `ACTIVE`)

Limits policies are seeded for:
- `PIX`
- `BOLETO`
- `TED`
- `CARD`

Important: if you call the API with a non-seeded customer, you receive `validation_error` (`Customer not found`).

## 6. API Contract

### POST `/payments`

Required headers:
- `Idempotency-Key`
- `X-Merchant-Id`
- `X-Customer-Id`
- `X-Account-Id`

Body:
- `amount` (decimal, `> 0`)
- `currency` (3-char code, normalized to uppercase)
- `method` (`PIX|BOLETO|TED|CARD`, strict enum value)
- `destination` (optional)
- `metadata` (optional JSON object)

Response:
- HTTP `202`
- `payment_id`
- `status`
- `trace_id`
- `risk_decision`
- `aml_decision`

### GET `/payments/{payment_id}`

Returns persisted status and metadata (`status`, timestamps, `risk_score`, decisions, `last_error`).

### POST `/review/{payment_id}/approve`

Approves an `IN_REVIEW` payment:
- status transitions to `RECEIVED`
- emits `PaymentRequested` outbox event
- processor can continue normal provider flow

### POST `/review/{payment_id}/reject`

Rejects an `IN_REVIEW` payment:
- status transitions to `BLOCKED`
- writes `manual_review_rejected` as `last_error`

### Error response format

```json
{
  "error": {
    "category": "validation_error",
    "message": "..."
  }
}
```

Main categories:
- `validation_error`
- `idempotency_conflict`
- `concurrency_conflict`
- `kyc_denied`
- `limit_exceeded`
- `rate_limited`
- `unexpected`

## 7. Control Pipeline Semantics

For `POST /payments`, current sequence is:
1. Schema + headers validation.
2. Customer lookup.
3. KYC + customer status enforcement.
4. Limits enforcement (transaction, daily, velocity).
5. Rate limiting (merchant, customer, account).
6. Risk scoring.
7. AML checks.
8. Final decision:
   - `BLOCK` => payment persisted as `BLOCKED` (no provider call).
   - `REVIEW` => payment persisted as `IN_REVIEW` + review event.
   - `ALLOW` => payment persisted as `RECEIVED` + `PaymentRequested` outbox event.

Supported statuses:
- `RECEIVED`
- `VALIDATED`
- `IN_REVIEW`
- `PROCESSING`
- `CONFIRMED`
- `FAILED`
- `BLOCKED`

## 8. Reproducible Control Scenarios

### 8.1 ALLOW

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-allow-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":100.00,"currency":"BRL","method":"PIX","destination":"dest-safe-001"}'
```

Expected:
- `status`: `RECEIVED` (then async progression to `CONFIRMED` by processor).

### 8.2 KYC denial (TED requires FULL)

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-kyc-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":500.00,"currency":"BRL","method":"TED"}'
```

Expected:
- HTTP `403`
- `error.category = "kyc_denied"`.

### 8.3 AML block by destination

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-aml-block-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-full-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":50.00,"currency":"BRL","method":"PIX","destination":"dest-blocked-001"}'
```

Expected:
- `status`: `BLOCKED`.

### 8.4 IN_REVIEW + manual decision

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-review-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":4600.00,"currency":"BRL","method":"PIX","destination":"dest-new-review-001"}'
```

Expected:
- `status`: `IN_REVIEW`.

Approve:

```bash
curl -s -X POST http://localhost:8080/review/<payment_id>/approve
```

Reject:

```bash
curl -s -X POST http://localhost:8080/review/<payment_id>/reject
```

### 8.5 Idempotency replay consistency

Send the same `Idempotency-Key` twice with same merchant:
- second response should replay the same payload/snapshot, including identical `payment_id`.

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-replay-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":90.00,"currency":"BRL","method":"PIX"}'
```

Repeat exactly the same command above and compare both responses.

### 8.6 Rate limiting (fixed window)

With default limits, trigger by burst:

```bash
for i in $(seq 1 140); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/payments \
    -H 'Content-Type: application/json' \
    -H "Idempotency-Key: idem-rate-$i" \
    -H 'X-Merchant-Id: merchant-rate' \
    -H 'X-Customer-Id: customer-basic-001' \
    -H 'X-Account-Id: account-rate' \
    -d '{"amount":10.00,"currency":"BRL","method":"PIX"}'
done
```

Expected:
- eventually receives HTTP `429` (`rate_limited`).

### 8.7 BDD Scenarios (Given/When/Then)

The following BDD scenarios reflect the current implementation and automated test coverage.

Implemented scenarios:

```gherkin
Feature: Payment controls and resilience

  Scenario: KYC blocks insufficient level for rail
    Given a customer with BASIC KYC
    When the customer creates a payment with method TED
    Then the API returns 403 with category "kyc_denied"

  Scenario: Suspended customer cannot initiate outgoing payments
    Given a customer with status SUSPENDED
    When the customer creates a payment
    Then the API denies the request

  Scenario: Daily limit is exceeded
    Given an existing daily outgoing amount near policy limit
    When a new payment exceeds the daily threshold
    Then the request is rejected with category "limit_exceeded"

  Scenario: Velocity limit under concurrency
    Given multiple concurrent requests for the same customer and rail
    When request count exceeds velocity policy in the time window
    Then at least one request is rejected with category "limit_exceeded"

  Scenario: AML blocks high-risk destination
    Given destination is in AML blocklist
    When a payment is evaluated
    Then AML decision is BLOCK and payment status becomes BLOCKED

  Scenario: AML detects structuring
    Given recent payments in 95-100 percent of rail max amount
    When another near-threshold payment is evaluated
    Then AML decision is REVIEW

  Scenario: Risk engine blocks high-risk context
    Given high amount, velocity pressure, repeated failures, and new destination
    When risk score is evaluated
    Then risk decision is BLOCK

  Scenario: Rate limiter protects API boundary
    Given repeated requests in the same rate-limit window
    When configured limit is exceeded
    Then API returns 429 with category "rate_limited"

  Scenario: Idempotency replay consistency under concurrency
    Given concurrent requests with same merchant and idempotency key
    When payment creation is executed
    Then all responses return the same payment_id and consistent status

  Scenario: Outbox worker confirms payment
    Given a pending PaymentRequested outbox event
    When worker processes the event and provider confirms
    Then payment is confirmed and PaymentConfirmed event is emitted
```

Planned BDD scenarios (recommended next):

```gherkin
Feature: End-to-end operational behaviors

  Scenario: REVIEW payment approved manually and then confirmed asynchronously
    Given a payment with status IN_REVIEW
    When /review/{payment_id}/approve is called
    Then status changes to RECEIVED and processor eventually confirms the payment

  Scenario: REVIEW payment rejected manually
    Given a payment with status IN_REVIEW
    When /review/{payment_id}/reject is called
    Then status changes to BLOCKED with reason manual_review_rejected

  Scenario: Processor retries transient provider failures
    Given provider returns timeout or 5xx
    When worker executes provider call
    Then retries follow backoff policy and avoid retry storm

  Scenario: Redis unavailable fallback
    Given Redis is unavailable
    When limits or AML checks execute
    Then service falls back to Postgres-based checks without crashing
```

## 9. Observability (Local-First)

### Tracing

Key spans:
- `validate`
- `kyc_check`
- `limits_check`
- `rate_limit_check`
- `risk_score`
- `aml_check`
- `outbox_process` (processor worker)
- HTTP middleware spans (`<METHOD> <PATH>`) in API and provider-mock

### Metrics

Examples:
- `kyc_check_duration`, `kyc_denied_total`
- `limits_check_duration`, `limits_exceeded_total`
- `rate_limited_total`
- `risk_decisions_total`, `aml_decisions_total`
- `review_queue_size`
- `idempotency_replay_total`
- provider/worker metrics for latency, errors, backlog, lag

### Logs

JSON logs with correlation fields:
- `trace_id`
- `payment_id`
- `idempotency_key`
- `merchant_id`
- `customer_id`
- `account_id`
- `rail`
- `risk_decision`
- `aml_decision`
- `status`

Sensitive destination and card-like values are redacted by formatter rules.

### Exporters

Current default:
- `OTEL_TRACES_EXPORTER=console`
- `OTEL_METRICS_EXPORTER=console`

No Grafana/collector stack is configured yet (intentional for local-first baseline).

## 10. Quality Gates and Testing

Install dependencies:

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry install
```

Run quality checks:

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run ruff check .
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run black --check .
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run mypy shared services/payments-api services/payments-processor services/provider-mock
```

Run tests (default excludes integration marker):

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run pytest
```

Run unit-only and integration-only:

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run pytest -m "not integration"
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run pytest -m integration
```

Coverage:
- Gate is `--cov-fail-under=88`.
- Coverage scope is currently focused on deterministic modules:
  - `shared/constants`, `shared/contracts`, `shared/resilience`, `shared/utils`
  - `payments_api.services`
  - `payments_api.use_cases.create_payment`
  - `payments_processor.providers.factory`
  - `payments_processor.providers.strategy`

## 11. Load Test Plan (Week 2)

Current status:
- No executable load test scripts are committed yet.
- Directory reserved for future scripts: `scripts/loadtest`.

Planned tools:
- `k6` for burst and sustained throughput scenarios.
- `locust` for mixed user-journey traffic across payment rails.

Initial target scenarios:
- High concurrency with repeated idempotency keys.
- Rate-limit pressure by merchant/customer/account.
- Risk and AML decision distribution under mixed traffic.
- Outbox backlog growth and processor lag under provider fault injection.

When adding scripts, each script should define:
- deterministic seeds/inputs,
- target endpoints and headers,
- expected success/failure criteria,
- metrics to collect (`p95`, error rate, status distribution).

## 12. CI/CD Pipelines

Workflows:
- `.github/workflows/ci.yml`
- `.github/workflows/cd.yml`

CI:
- triggers on PR and push (`main`, `develop`).
- runs lint, format check, mypy, unit tests with coverage gate.
- validates Docker Compose syntax.

CD:
- triggers on tags `v*` or manual dispatch.
- builds images for all 3 services.
- optionally pushes to GHCR.

## 13. Environment Variables

Reference file:
- `.env.example`

Main runtime variables:
- `APP_ENV`
- `LOG_LEVEL`
- `POSTGRES_DSN`
- `REDIS_URL`
- `MERCHANT_RATE_LIMIT`
- `CUSTOMER_RATE_LIMIT`
- `ACCOUNT_RATE_LIMIT`
- `RATE_LIMIT_WINDOW_SECONDS`
- `AML_TOTAL_WINDOW_SECONDS`
- `AML_TOTAL_THRESHOLD_AMOUNT`
- `AML_STRUCTURING_WINDOW_SECONDS`
- `AML_STRUCTURING_COUNT_THRESHOLD`
- `AML_BLOCKLIST_DESTINATIONS_CSV`
- provider simulation knobs:
  - `RANDOM_SEED`
  - `FAULT_5XX_RATE`
  - `TIMEOUT_RATE`
  - `LATENCY_SPIKE_RATE`
  - `DUPLICATE_RATE`
  - `PARTIAL_FAILURE_RATE`

Notes:
- For Docker Compose quick start, defaults in `infra/docker/docker-compose.yml` are enough.
- Use `.env` when running services directly with Poetry.

## 14. Troubleshooting

### Docker compose appears stuck

Cause:
- Docker Desktop paused or starting.

Checks:

```bash
docker desktop status
docker compose -f infra/docker/docker-compose.yml ps
```

### Healthcheck never becomes healthy

Check logs:

```bash
docker compose -f infra/docker/docker-compose.yml logs payments-api --tail=200
docker compose -f infra/docker/docker-compose.yml logs payments-processor --tail=200
docker compose -f infra/docker/docker-compose.yml logs provider-mock --tail=200
```

### `Customer not found`

You are likely using a non-seeded customer header.
Use one of:
- `customer-basic-001`
- `customer-full-001`
- `customer-suspended-001`
- `customer-none-001`

### Port already in use

Find and stop conflicting process/container, or free ports:
- `5432`, `6379`, `8080`, `8082`.

### `poetry install` fails

Check:
- internet connectivity to package index.
- Python version (`3.12`) compatibility.

## 15. Security and Privacy Notes

- Logs redact sensitive destination and card-like data.
- Only synthetic identifiers are used in examples.
- No real customer or payment instrument data should be stored in this lab.

## 16. Week 2 Expansion TODO

1. Add queue adapter (Kafka/Rabbit) for review/event fan-out.
2. Add approval SLA monitoring for `IN_REVIEW`.
3. Add migration workflow with Alembic.
4. Expand AML scenarios (rapid in-out with synthetic incoming ledger).
5. Add load test implementations in `scripts/loadtest`.
6. Add local OTel collector/dashboard stack (still no external SaaS required).
