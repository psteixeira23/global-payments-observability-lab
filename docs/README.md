# Documentation Index

This folder contains the detailed documentation for `global-payments-observability-lab`.

## Start Here

1. `getting-started.md`
2. `api-reference.md`
3. `control-scenarios.md`

## Reference Guides

- `observability.md`
- `quality-and-testing.md`
- `operations.md`
- `architecture/patterns.md`
- `../scripts/loadtest/README.md`

## Monitoring Endpoints

- Grafana credentials are configured via `.env`:
  - `GRAFANA_ADMIN_USER`
  - `GRAFANA_ADMIN_PASSWORD`
- API health: `http://localhost:8080/health`
- Grafana home: `http://localhost:3000`
- Grafana folder: `http://localhost:3000/dashboards/f/cfcnhdf7apybka/payments-observability`
- Grafana main dashboard: `http://localhost:3000/d/payments-observability-overview/payments-observability-overview`
- Prometheus home: `http://localhost:9090`
- Prometheus graph: `http://localhost:9090/graph`
- Prometheus targets: `http://localhost:9090/targets`
- Prometheus alerts/rules: `http://localhost:9090/rules`
- Provider health: `http://localhost:8082/health`
- Jaeger search: `http://localhost:16686/search`
- RabbitMQ management (queue profile): `http://localhost:15672`
- API docs: `http://localhost:8080/docs`
- Provider docs: `http://localhost:8082/docs`

## Infrastructure Assets

- `../infra/observability/otel-collector-config.yaml`
- `../infra/observability/prometheus.yml`
- `../infra/observability/grafana/`

## Evidence

- `evidence/smoke-tests.md`
