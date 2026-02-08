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

Default local configuration:

- `OTEL_TRACES_EXPORTER=console`
- `OTEL_METRICS_EXPORTER=console`

No external dashboards are configured in this baseline by design.

## Local Visualization Stack

This project now includes an optional local visualization profile:

- OpenTelemetry Collector
- Jaeger (traces)
- Prometheus (metrics storage/query)
- Grafana (dashboards)

Start command:

```bash
OTEL_TRACES_EXPORTER=otlp OTEL_METRICS_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318 \
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
docker compose -f infra/docker/docker-compose.yml --profile observability up -d --build
```

UIs:

- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)

## Executive Metrics for Reporting

The provisioned Grafana dashboard `Payments Observability Overview` includes:

- API request rate
- API error rate
- API latency quantiles (`P50`, `P95`, `P99`)
- rate limiting rate (including per dimension)
- provider latency and provider error rate
- outbox lag and backlog indicators
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
