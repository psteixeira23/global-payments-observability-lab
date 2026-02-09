# Observability (Local-First)

## Tracing

Representative spans:

- `validate`
- `kyc_check`
- `limits_check`
- `rate_limit_check`
- `risk_score`
- `aml_check`
- `outbox_process`
- `<METHOD> <PATH>` middleware spans

Trace propagation is preserved between API, worker, and provider calls.

## Metrics

Examples:

- `kyc_check_duration`, `kyc_denied_total`
- `limits_check_duration`, `limits_exceeded_total`
- `rate_limited_total`
- `risk_decisions_total`, `aml_decisions_total`
- `review_queue_size`
- `idempotency_replay_total`
- provider latency/error metrics
- outbox backlog and lag metrics
- fan-out backlog, publish latency, and publish error metrics

## Structured Logs

Log format: JSON with correlation fields.

Main fields:

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

Security behavior:

- destination-like sensitive fields are redacted
- card-like numeric patterns are redacted

## Exporters

Docker Compose local default:

- `OTEL_TRACES_EXPORTER=otlp`
- `OTEL_METRICS_EXPORTER=otlp`
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`

Note:

- If you run services directly outside Docker Compose, application-level fallback remains `console`.

## Local Visualization Stack

This project now includes an optional local visualization profile:

- OpenTelemetry Collector
- Jaeger (traces)
- Prometheus (metrics storage/query)
- Grafana (dashboards)
- Optional RabbitMQ/Kafka profile for event fan-out simulation

Start command:

```bash
docker compose -f infra/docker/docker-compose.yml --profile observability up -d --build
```

UIs:

- `docs/README.md#monitoring-endpoints`
- Grafana credentials come from `.env` values:
  - `GRAFANA_ADMIN_USER`
  - `GRAFANA_ADMIN_PASSWORD`

## Troubleshooting Blank Grafana Panels

1. Recreate observability stack and services:

```bash
docker compose -f infra/docker/docker-compose.yml --profile observability up -d --force-recreate
```

2. Generate traffic:

```bash
for i in $(seq 1 20); do
  curl -s -o /dev/null -X POST http://localhost:8080/payments \
    -H 'Content-Type: application/json' \
    -H "Idempotency-Key: obs-panel-$i" \
    -H 'X-Merchant-Id: merchant-obs-001' \
    -H 'X-Customer-Id: customer-basic-001' \
    -H 'X-Account-Id: account-obs-001' \
    -d '{"amount":100.00,"currency":"BRL","method":"PIX","destination":"dest-obs-001"}'
done
```

3. Confirm Prometheus has data:

```bash
curl -s 'http://localhost:9090/api/v1/query?query=payments_api_request_total'
```

4. Hard refresh Grafana (`Cmd+Shift+R`) and set time range to `Last 30 minutes`.

## Executive Metrics for Reporting

The provisioned Grafana dashboard `Payments Observability Overview` includes:

- API request rate
- API error rate
- API latency quantiles (`P50`, `P95`, `P99`)
- rate limiting rate (including per dimension)
- provider latency and provider error rate
- outbox lag and backlog indicators
- fan-out backlog, fan-out publish latency, and fan-out publish errors
- risk and AML decision rates

This is the recommended view for management-level progress and SLA discussions.

## PromQL Cheat Sheet

Use these queries in Prometheus or Grafana Explore:

- API `P50` latency (ms):
  - `histogram_quantile(0.50, sum(rate(payments_api_request_latency_ms_bucket[5m])) by (le))`
- API `P95` latency (ms):
  - `histogram_quantile(0.95, sum(rate(payments_api_request_latency_ms_bucket[5m])) by (le))`
- API `P99` latency (ms):
  - `histogram_quantile(0.99, sum(rate(payments_api_request_latency_ms_bucket[5m])) by (le))`
- request throughput:
  - `sum(rate(payments_api_request_total[5m]))`
- error throughput:
  - `sum(rate(payments_api_error_total[5m]))`
- rate-limited throughput by dimension:
  - `sum(rate(rate_limited_total[5m])) by (dimension)`
- rate-limited volume by dimension (last 15m):
  - `sum(increase(rate_limited_total[15m])) by (dimension)`
- fan-out publish error throughput:
  - `sum(rate(payments_processor_fanout_publish_errors[5m]))`
- fan-out publish `P99` latency (ms):
  - `histogram_quantile(0.99, sum(rate(payments_processor_fanout_publish_latency_ms_bucket[5m])) by (le))`

## Alert Rules

Local Prometheus alert rules are provisioned from:

- `infra/observability/prometheus-alerts.yml`

Current baseline alerts:

- API `p99` latency high
- API error rate high
- outbox lag high
- manual review queue growth

## Demo: Force Rate Limiting for Presentation

For a controlled demo (without code changes), temporarily lower the limits:

```bash
MERCHANT_RATE_LIMIT=3 CUSTOMER_RATE_LIMIT=3 ACCOUNT_RATE_LIMIT=3 \
OTEL_TRACES_EXPORTER=otlp OTEL_METRICS_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318 \
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
docker compose -f infra/docker/docker-compose.yml --profile observability up -d --force-recreate payments-api
```

Then run 5-10 rapid `POST /payments` calls with the same merchant/customer/account and observe `429` + `rate_limited_total`.
