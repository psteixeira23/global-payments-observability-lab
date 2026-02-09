# global-payments-observability-lab

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=alert_status&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=bugs&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=code_smells&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=coverage&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=duplicated_lines_density&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=vulnerabilities&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)

Local-first engineering lab for fintech payment observability and deterministic control layers.

## Language and Runtime

- Language: `Python`
- Runtime version: `3.12`
- Documentation and source code language: `English`

## Stack

- API framework: `FastAPI`
- ASGI server: `Uvicorn`
- Database: `PostgreSQL` + `SQLAlchemy 2.0 (async)` + `asyncpg`
- Cache and fast counters: `Redis`
- HTTP client: `httpx`
- Testing: `pytest`, `pytest-asyncio`, `pytest-cov`
- Quality: `ruff`, `black`, `mypy`, `SonarCloud`
- Dependency management: `Poetry`
- Local orchestration: `Docker Compose`

## What You Get

- Three services: `payments-api`, `payments-processor`, `provider-mock`.
- Deterministic controls: KYC, limits, rate limiting, risk scoring, AML.
- Async processing with outbox polling and provider simulation.
- Optional event fan-out adapter for RabbitMQ- or Kafka-backed queue publishing.
- Structured logs, traces, and metrics (no external SaaS required).

## Not for Production

This repository is a **laboratory project** and is not production-ready by default.

- It is designed for deterministic experimentation, observability practice, and resilience exercises.
- Security controls are intentionally minimal and configurable for local iteration speed.
- Deploying this stack to the public internet without additional controls is unsafe.

## Minimal Threat Model

- Assets:
  - payment state in Postgres
  - control decisions (KYC/AML/risk) and outbox events
  - observability telemetry and logs
- Primary threats:
  - unauthorized API access
  - credential leakage in config/docs
  - traffic interception without TLS
  - abuse via bot traffic / replay / brute force
  - sensitive data exposure in logs
- Current baseline controls:
  - idempotency + scoped rate limits
  - CORS allow-list
  - baseline HTTP security headers
  - optional bearer token at API boundary
  - redaction for destination/card-like log fields
  - non-root runtime users in service containers
- Residual risks:
  - no full IAM/OIDC authorization model
  - no mTLS between services
  - local secret management only
  - no WAF/edge DDoS controls

## Hardening Checklist

- [x] Non-root containers for application services
- [x] CORS allow-list on HTTP services
- [x] Baseline security headers (`nosniff`, `frame deny`, CSP, referrer policy)
- [x] Optional bearer auth for `payments-api` routes (`API_AUTH_ENABLED=true`)
- [x] Scoped rate limiting (`merchant`, `customer`, `account`)
- [x] Structured logging with redaction for sensitive destination/card-like fields
- [ ] OIDC/JWT authN+authZ with tenant-aware roles
- [ ] End-to-end TLS + mTLS between internal services
- [ ] Secret manager integration (Vault/AWS/GCP) with rotation
- [ ] Edge hardening (WAF, bot protection, DDoS controls, API gateway policies)

## Prerequisites

- Docker Desktop running (not paused)
- Docker Compose v2 (`docker compose`)
- Free ports: `5432`, `6379`, `8080`, `8082`

Optional ports for local observability and queue profiles:

- `16686` (Jaeger)
- `3000` (Grafana)
- `9090` (Prometheus)
- `4317`, `4318`, `8889` (OTel collector endpoints)
- `5672`, `15672` (RabbitMQ)
- `19092`, `18083` (Kafka/Redpanda external ports)

Optional for local development outside containers:

- `Python 3.12`
- `Poetry 1.8+`

Validation:

```bash
docker --version
docker compose version
python3 --version
poetry --version
```

## Repository Structure

```text
.
├── services/
│   ├── payments-api/
│   ├── payments-processor/
│   └── provider-mock/
├── shared/
├── tests/
├── infra/
│   ├── docker/
│   └── observability/
├── docs/
└── scripts/
```

## Architecture and Design Patterns

The project uses Layered + Ports and Adapters with explicit Outbox, Strategy, Factory, Repository, Adapter, Retry, Circuit Breaker, and Bulkhead patterns.

Detailed architecture, trade-offs, extension rules, and pattern map:

- `docs/architecture/patterns.md`

## Quick Start

```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
docker compose -f infra/docker/docker-compose.yml ps
curl -s http://localhost:8080/health
curl -s http://localhost:8082/health
```

Enable local observability UIs:

```bash
docker compose -f infra/docker/docker-compose.yml --profile observability up -d
```

Create a payment:

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: quickstart-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":100.00,"currency":"BRL","method":"PIX","destination":"dest-safe-001"}'
```

Follow logs:

```bash
docker compose -f infra/docker/docker-compose.yml logs -f payments-api payments-processor provider-mock
```

Stop stack:

```bash
docker compose -f infra/docker/docker-compose.yml down
```

Reset stack state (recommended before deterministic scenario replay):

```bash
docker compose -f infra/docker/docker-compose.yml down -v
docker compose -f infra/docker/docker-compose.yml up -d --build
```

Run local quality checks:

```bash
poetry install
poetry run ruff check .
poetry run black --check .
poetry run pytest -q
```

## Local URLs

- API health: `http://localhost:8080/health`
- API docs: `http://localhost:8080/docs`
- Provider health: `http://localhost:8082/health`
- Provider docs: `http://localhost:8082/docs`
- Monitoring dashboards and observability URLs: `docs/README.md#monitoring-endpoints`

## Observability Quick Check

If Grafana charts are blank, run this quick flow:

```bash
docker compose -f infra/docker/docker-compose.yml --profile observability up -d --force-recreate

for i in $(seq 1 20); do
  curl -s -o /dev/null -X POST http://localhost:8080/payments \
    -H 'Content-Type: application/json' \
    -H "Idempotency-Key: obs-check-$i" \
    -H 'X-Merchant-Id: merchant-obs-001' \
    -H 'X-Customer-Id: customer-basic-001' \
    -H 'X-Account-Id: account-obs-001' \
    -d '{"amount":100.00,"currency":"BRL","method":"PIX","destination":"dest-obs-001"}'
done
```

Validate metrics in Prometheus:

```bash
curl -s 'http://localhost:9090/api/v1/query?query=payments_api_request_total'
```

Then open:

- `http://localhost:3000/d/payments-observability-overview/payments-observability-overview`

## Documentation

Full documentation is organized under `docs/`:

- `docs/README.md`: documentation index.
- `docs/getting-started.md`: prerequisites, startup, seeded data.
- `docs/api-reference.md`: endpoints, contracts, and errors.
- `docs/control-scenarios.md`: reproducible control paths with `curl`.
- `docs/observability.md`: traces, metrics, logs, exporters.
- `docs/quality-and-testing.md`: lint, type checks, tests, coverage, CI/CD.
- `docs/operations.md`: environment variables and troubleshooting.
- `docs/evidence/smoke-tests.md`: smoke test evidence.
- `docs/architecture/patterns.md`: patterns and design references.
- `scripts/loadtest/README.md`: high-throughput load-testing runbook (`k6`).

## License

This project is licensed under the MIT License. See `LICENSE`.

> "Simplicity is prerequisite for reliability." - Edsger W. Dijkstra
