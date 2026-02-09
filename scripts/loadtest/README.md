# Load Testing Runbook

This folder contains executable load-test scripts designed for high-throughput fintech simulation.

## Goals

- Validate mixed payment traffic under sustained load.
- Track `p50`, `p95`, `p99`, error rate, and control-path distribution.
- Stress idempotency behavior under high concurrency.

## Tooling

- `k6` (recommended baseline)

Install:

```bash
brew install k6
```

## Prerequisites

Start the platform:

```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
```

Health checks:

```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8082/health
```

Authentication note:

- Current scripts do not inject bearer token headers.
- Run load tests with `API_AUTH_ENABLED=false`, or extend the scripts before testing authenticated mode.

## Scripts

- `k6/mixed_rails_traffic.js`: sustained mixed rail traffic with optional high target RPS.
- `k6/idempotency_collision.js`: concurrent replay stress for idempotency guarantees.

## Baseline Run (local laptop-safe)

```bash
BASE_URL=http://localhost:8080 \
TARGET_RPS=200 \
TEST_DURATION=2m \
PREALLOCATED_VUS=300 \
MAX_VUS=800 \
k6 run scripts/loadtest/k6/mixed_rails_traffic.js
```

## High Throughput Run (target 5k TPS)

Use only on a dedicated machine/runner with enough CPU/network:

```bash
BASE_URL=http://localhost:8080 \
TARGET_RPS=5000 \
TEST_DURATION=5m \
PREALLOCATED_VUS=6000 \
MAX_VUS=12000 \
k6 run scripts/loadtest/k6/mixed_rails_traffic.js
```

## Idempotency Concurrency Run

```bash
BASE_URL=http://localhost:8080 \
IDEMPOTENCY_VUS=300 \
IDEMPOTENCY_ITERATIONS=300 \
k6 run scripts/loadtest/k6/idempotency_collision.js
```

## Metrics to Watch

From k6 output:

- `http_req_duration`: `p(50)`, `p(95)`, `p(99)`
- `http_req_failed`
- custom trends:
  - `payment_create_latency`
  - `payment_status_query_latency`
- custom counters:
  - decision distribution (`ALLOW`, `BLOCKED`, `IN_REVIEW`)
  - error categories (`429`, `403`, `422`, `5xx`)

From app stack:

- API and processor logs:

```bash
docker compose -f infra/docker/docker-compose.yml logs -f payments-api payments-processor
```

- Optional dashboards with profile:

```bash
docker compose -f infra/docker/docker-compose.yml --profile observability up -d
```

## Throughput Notes

- Default app limits are intentionally strict for control validation. For pure throughput benchmarking, use:
  - many merchant/customer/account IDs (already done in scripts),
  - a clean DB/Redis state before each run,
  - tuned rate-limit env vars when needed.
- Provider fault injection affects tail latency and failure rates by design.
