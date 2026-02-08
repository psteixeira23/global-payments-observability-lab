# Getting Started

## Prerequisites

Required:

- Docker Desktop running (not paused).
- Docker Compose v2 (`docker compose`).
- Free local ports: `5432`, `6379`, `8080`, `8082`.

Optional (for local development outside containers):

- Python `3.12`.
- Poetry `1.8+`.

Validation commands:

```bash
docker --version
docker compose version
python3 --version
poetry --version
```

## Run the Platform

```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
docker compose -f infra/docker/docker-compose.yml ps
```

Optional: start with local observability stack (Jaeger, Prometheus, Grafana):

```bash
OTEL_TRACES_EXPORTER=otlp OTEL_METRICS_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318 \
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
docker compose -f infra/docker/docker-compose.yml --profile observability up -d --build
```

Expected services:

- `payments-api` on `8080`.
- `provider-mock` on `8082`.
- `payments-processor` background worker.
- `postgres` and `redis`.

## Health Checks

```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8082/health
```

Both should return:

```json
{"status":"ok"}
```

## Seeded Data (Local)

When `APP_ENV=local`, API startup initializes schema and seeds baseline data.

Seeded customers:

- `customer-basic-001` (`BASIC`, `ACTIVE`)
- `customer-full-001` (`FULL`, `ACTIVE`)
- `customer-suspended-001` (`FULL`, `SUSPENDED`)
- `customer-none-001` (`NONE`, `ACTIVE`)

Recommendation:

- use `customer-full-001` for repeat `IN_REVIEW` demo scenarios to avoid KYC and reduce chance of hitting PIX limits from prior local runs.

Seeded limits policy rails:

- `PIX`
- `BOLETO`
- `TED`
- `CARD`

## First Payment

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: quickstart-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":100.00,"currency":"BRL","method":"PIX","destination":"dest-safe-001"}'
```

Query payment by `payment_id`:

```bash
curl -s http://localhost:8080/payments/<payment_id>
```

## Useful URLs

- API docs: `http://localhost:8080/docs`
- Provider docs: `http://localhost:8082/docs`
- Jaeger UI: `http://localhost:16686` (when profile is enabled)
- Prometheus UI: `http://localhost:9090` (when profile is enabled)
- Grafana UI: `http://localhost:3000` (when profile is enabled)

## Stop and Reset

Stop:

```bash
docker compose -f infra/docker/docker-compose.yml down
```

Stop and remove volumes:

```bash
docker compose -f infra/docker/docker-compose.yml down -v
```
