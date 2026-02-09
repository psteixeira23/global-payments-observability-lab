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

Optional but recommended before startup:

```bash
cp .env.example .env
```

```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
docker compose -f infra/docker/docker-compose.yml ps
```

Optional: start with local observability stack (Jaeger, Prometheus, Grafana):

```bash
docker compose -f infra/docker/docker-compose.yml --profile observability up -d --build
```

Optional: run with edge hardening overlay (TLS gateway + reduced host exposure for internal services):

```bash
docker compose -f infra/docker/docker-compose.yml -f infra/docker/docker-compose.edge.yml --profile edge up -d --build
```

Quick metrics check:

```bash
curl -s 'http://localhost:9090/api/v1/query?query=up'
```

Optional: start queue profile services (RabbitMQ + Kafka/Redpanda):

```bash
docker compose -f infra/docker/docker-compose.yml --profile queue up -d rabbitmq kafka
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

Authentication note:

- By default, local docker setup runs with `API_AUTH_ENABLED=false`.
- If you enable auth, include `Authorization: Bearer <API_AUTH_TOKEN>` on all `payments-api` requests.

Query payment by `payment_id`:

```bash
curl -s http://localhost:8080/payments/<payment_id>
```

## Useful URLs

- Monitoring and dashboard URLs: `docs/README.md#monitoring-endpoints`
- Edge HTTPS health (if edge profile is enabled): `https://localhost:8443/health`

## Stop and Reset

Stop:

```bash
docker compose -f infra/docker/docker-compose.yml down
```

Stop and remove volumes:

```bash
docker compose -f infra/docker/docker-compose.yml down -v
```
