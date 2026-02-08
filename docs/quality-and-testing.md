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

## Coverage Gate

Current configured minimum coverage:

- `--cov-fail-under=88`

Coverage scope includes:

- `shared/constants`
- `shared/contracts`
- `shared/resilience`
- `shared/utils`
- `payments_api.services`
- `payments_api.use_cases.create_payment`
- `payments_processor.providers.factory`
- `payments_processor.providers.strategy`

## CI/CD

Workflows:

- `.github/workflows/ci.yml`
- `.github/workflows/cd.yml`

CI includes:

- lint
- format check
- mypy
- tests with coverage gate
- Docker Compose validation

CD includes:

- image build for all services
- optional GHCR push on tags `v*` or manual dispatch
