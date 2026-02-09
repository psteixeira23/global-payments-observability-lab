# Quality and Testing

## Install

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry install
```

## Lint and Type Checks

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run ruff check .
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run black --check .
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run mypy shared services/payments-api services/payments-processor services/provider-mock
```

## Test Commands

Run default test suite:

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run pytest
```

Run unit-only and integration-only:

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run pytest -m "not integration"
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run pytest -m integration
```

Generate `coverage.xml` for Sonar:

```bash
POETRY_VIRTUALENVS_IN_PROJECT=true poetry run pytest -q --maxfail=1 --disable-warnings \
  -o addopts="" \
  -m "not integration" \
  --cov=services --cov=shared \
  --cov-report=xml:coverage.xml \
  --cov-report=term-missing
```

## Coverage Gate

Current configured minimum coverage:

- `--cov-fail-under=88`

Coverage scope includes:

- `services/**`
- `shared/**`

## CI/CD

Workflows:

- `.github/workflows/ci.yml`
- `.github/workflows/cd.yml`
- `.github/workflows/sonarcloud.yml`
- `.github/workflows/loadtest-5k-evidence.yml`

CI includes:

- lint
- format check
- mypy
- tests with coverage gate
- Docker Compose validation

CD includes:

- image build for all services
- optional GHCR push on tags `v*` or manual dispatch

SonarCloud workflow includes:

- test execution with `coverage.xml` generation
- scanner execution on `main` and pull requests

## SonarCloud Re-Run and Quality Gate Validation

After merging hardening/test updates, run SonarCloud pipeline again and validate gate:

1. Push changes to the target branch.
2. Confirm `.github/workflows/sonarcloud.yml` finished successfully.
3. Validate in SonarCloud:
   - `Coverage on New Code`
   - `Reliability`
   - `Security`
   - `Maintainability`
   - Quality Gate status = `Passed`

## Database Migration Workflow (Alembic)

Apply migrations:

```bash
POSTGRES_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/payments \
poetry run alembic upgrade head
```

Create a new migration revision:

```bash
poetry run alembic revision -m "describe_change"
```

## Load Testing

Run mixed traffic baseline:

```bash
k6 run scripts/loadtest/k6/mixed_rails_traffic.js
```

Run idempotency collision stress:

```bash
k6 run scripts/loadtest/k6/idempotency_collision.js
```

Detailed runbook:

- `scripts/loadtest/README.md`
- Continuous 5k TPS evidence workflow:
  - `.github/workflows/loadtest-5k-evidence.yml`
  - requires a dedicated self-hosted runner labeled: `self-hosted`, `linux`, `x64`, `loadtest`

## Queue Fan-out Smoke (Optional)

RabbitMQ backend:

```bash
EVENT_BUS_BACKEND=rabbitmq \
EVENT_BUS_URL=amqp://guest:guest@rabbitmq:5672/ \
docker compose -f infra/docker/docker-compose.yml --profile queue up -d rabbitmq --force-recreate payments-processor
```

Kafka backend:

```bash
EVENT_BUS_BACKEND=kafka \
EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
EVENT_BUS_KAFKA_TOPIC=payments.domain-events \
docker compose -f infra/docker/docker-compose.yml --profile queue up -d kafka --force-recreate payments-processor
```
