# Operations Guide

## Environment Variables

Reference:

- `.env.example`

Recommended setup:

```bash
cp .env.example .env
```

Main variables:

- `APP_ENV`
- `LOG_LEVEL`
- `API_AUTH_ENABLED`
- `API_AUTH_TOKEN`
- `POSTGRES_DSN`
- `REDIS_URL`
- `CORS_ALLOWED_ORIGINS_CSV`
- `PROVIDER_MOCK_BASE_URL` (optional explicit full URL)
- `PROVIDER_MOCK_HOST` (used when full URL is not provided)
- `LOCAL_PROVIDER_SCHEME` (default `http`)
- `SECURE_PROVIDER_SCHEME` (default `https`)
- `EVENT_BUS_BACKEND` (`none`, `rabbitmq`, or `kafka`)
- `EVENT_BUS_URL` (used when backend is `rabbitmq`)
- `EVENT_BUS_EXCHANGE`
- `EVENT_BUS_ROUTING_PREFIX`
- `EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS` (used when backend is `kafka`)
- `EVENT_BUS_KAFKA_TOPIC`
- `GRAFANA_ADMIN_USER`
- `GRAFANA_ADMIN_PASSWORD`
- `RABBITMQ_DEFAULT_USER`
- `RABBITMQ_DEFAULT_PASS`
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
- For public demo environments, enable API auth and set a strong token.
- `payments-processor` resolves provider URL securely by default outside `APP_ENV=local`.
- Local docker flow intentionally uses HTTP between internal containers.
- Application containers run with a non-root runtime user (`appuser`) for least privilege.
- Optional queue profile can be enabled with RabbitMQ and Kafka for domain event fan-out.
- To enable dashboards and trace UI locally, start compose with profile `observability`.
- Edge hardening mode can be enabled with compose overlay `infra/docker/docker-compose.edge.yml`.

Out-of-scope by design in study mode:

- OIDC/JWT identity provider integration
- internal mTLS between microservices
- Vault/managed secrets and key rotation workflows

Start queue profile:

```bash
docker compose -f infra/docker/docker-compose.yml --profile queue up -d rabbitmq kafka
```

Start edge hardening profile:

```bash
docker compose -f infra/docker/docker-compose.yml -f infra/docker/docker-compose.edge.yml --profile edge up -d --build
```

Edge mode behavior:

- API ingress through TLS gateway (`https://localhost:8443`).
- direct host exposure for `payments-api`, `provider-mock`, `postgres`, and `redis` is removed.
- HTTP on `:8088` redirects to HTTPS on `:8443`.

Enable RabbitMQ fan-out in processor:

```bash
RABBITMQ_DEFAULT_USER=lab_rabbit_user \
RABBITMQ_DEFAULT_PASS=change-this-password \
EVENT_BUS_BACKEND=rabbitmq \
EVENT_BUS_URL=amqp://${RABBITMQ_DEFAULT_USER}:${RABBITMQ_DEFAULT_PASS}@rabbitmq:5672/ \
docker compose -f infra/docker/docker-compose.yml --profile queue up -d --force-recreate payments-processor
```

Enable Kafka fan-out in processor:

```bash
EVENT_BUS_BACKEND=kafka \
EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
EVENT_BUS_KAFKA_TOPIC=payments.domain-events \
docker compose -f infra/docker/docker-compose.yml --profile queue up -d --force-recreate payments-processor
```

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

### Grafana panels are blank

```bash
docker compose -f infra/docker/docker-compose.yml --profile observability up -d --force-recreate
curl -s 'http://localhost:9090/api/v1/query?query=payments_api_request_total'
```

If query result is empty, generate payment traffic and retry.

### Edge gateway smoke checks

```bash
curl -k -s -o /dev/null -w "edge /health -> %{http_code}\n" https://localhost:8443/health
curl -s -o /dev/null -w "redirect /health -> %{http_code}\n" http://localhost:8088/health
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
