# global-payments-observability-lab

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=alert_status&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=bugs&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=code_smells&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=coverage&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=duplicated_lines_density&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=psteixeira23_global-payments-observability-lab&metric=vulnerabilities&branch=main)](https://sonarcloud.io/summary/new_code?id=psteixeira23_global-payments-observability-lab&branch=main)

Local-first engineering lab for fintech payment observability and deterministic control layers.

## What You Get

- Three services: `payments-api`, `payments-processor`, `provider-mock`.
- Deterministic controls: KYC, limits, rate limiting, risk scoring, AML.
- Async processing with outbox polling and provider simulation.
- Structured logs, traces, and metrics (no external SaaS required).

## Quick Start

```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
docker compose -f infra/docker/docker-compose.yml ps
curl -s http://localhost:8080/health
curl -s http://localhost:8082/health
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

## Local URLs

- API health: `http://localhost:8080/health`
- API docs: `http://localhost:8080/docs`
- Provider health: `http://localhost:8082/health`
- Provider docs: `http://localhost:8082/docs`
- Jaeger UI (with observability profile): `http://localhost:16686`
- Grafana UI (with observability profile): `http://localhost:3000` (`admin` / `admin`)
- Grafana dashboard: `http://localhost:3000/d/payments-observability-overview/payments-observability-overview`
- Prometheus UI (with observability profile): `http://localhost:9090`

Enable local observability stack:

```bash
OTEL_TRACES_EXPORTER=otlp OTEL_METRICS_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318 \
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
docker compose -f infra/docker/docker-compose.yml --profile observability up -d --build
```

## Documentation

Full documentation is organized under `docs/`:

- `docs/README.md`: documentation index.
- `docs/getting-started.md`: prerequisites, startup, seeded data.
- `docs/api-reference.md`: endpoints, contracts, and errors.
- `docs/control-scenarios.md`: reproducible control paths with `curl`.
- `docs/observability.md`: traces, metrics, logs, exporters.
- `docs/quality-and-testing.md`: lint, type checks, tests, coverage, CI/CD.
- `docs/operations.md`: environment variables and troubleshooting.
- `docs/roadmap-week2.md`: expansion plan.
- `docs/evidence/smoke-tests-2026-02-08.md`: smoke test evidence.
- `docs/architecture/patterns.md`: patterns and design references.

## License

This project is licensed under the MIT License. See `LICENSE`.

> "Simplicity is prerequisite for reliability." - Edsger W. Dijkstra
