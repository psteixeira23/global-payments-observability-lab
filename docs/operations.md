# Operations Guide

## Environment Variables

Reference:

- `.env.example`

Main variables:

- `APP_ENV`
- `LOG_LEVEL`
- `POSTGRES_DSN`
- `REDIS_URL`
- `PROVIDER_MOCK_BASE_URL` (optional explicit full URL)
- `PROVIDER_MOCK_HOST` (used when full URL is not provided)
- `LOCAL_PROVIDER_SCHEME` (default `http`)
- `SECURE_PROVIDER_SCHEME` (default `https`)
- `MERCHANT_RATE_LIMIT`
- `CUSTOMER_RATE_LIMIT`
- `ACCOUNT_RATE_LIMIT`
- `RATE_LIMIT_WINDOW_SECONDS`
- `AML_TOTAL_WINDOW_SECONDS`
- `AML_TOTAL_THRESHOLD_AMOUNT`
- `AML_STRUCTURING_WINDOW_SECONDS`
- `AML_STRUCTURING_COUNT_THRESHOLD`
- `AML_BLOCKLIST_DESTINATIONS_CSV`

Provider simulation knobs:

- `RANDOM_SEED`
- `FAULT_5XX_RATE`
- `TIMEOUT_RATE`
- `LATENCY_SPIKE_RATE`
- `DUPLICATE_RATE`
- `PARTIAL_FAILURE_RATE`

Note:

- Docker Compose defaults are enough for quick local execution.
- `payments-processor` resolves provider URL securely by default outside `APP_ENV=local`.
- Local docker flow intentionally uses HTTP between internal containers.
- Application containers run with a non-root runtime user (`appuser`) for least privilege.
- To enable dashboards and trace UI locally, start compose with profile `observability`.

## Troubleshooting

### Docker appears stuck

```bash
docker desktop status
docker compose -f infra/docker/docker-compose.yml ps
```

### Services are unhealthy

```bash
docker compose -f infra/docker/docker-compose.yml logs payments-api --tail=200
docker compose -f infra/docker/docker-compose.yml logs payments-processor --tail=200
docker compose -f infra/docker/docker-compose.yml logs provider-mock --tail=200
```

### `Customer not found`

Use one seeded customer:

- `customer-basic-001`
- `customer-full-001`
- `customer-suspended-001`
- `customer-none-001`

### Port conflict

Free one of these ports:

- `5432`
- `6379`
- `8080`
- `8082`

### Poetry install issues

Validate:

- internet/package registry availability
- Python version compatibility
