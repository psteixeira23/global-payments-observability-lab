# Smoke Test Evidence

This file is the canonical smoke evidence log for the project.

## Latest Full Run - 2026-02-09

Execution timestamp (UTC): `2026-02-09T00:09:21Z`

Environment:

- Docker Desktop running
- Full stack up with observability services (`Grafana`, `Prometheus`, `Jaeger`, `OTel Collector`)
- Services healthy before scenario execution

### Commands Used

```bash
docker compose -f infra/docker/docker-compose.yml up -d --build
docker compose -f infra/docker/docker-compose.yml ps
```

```bash
curl -s -o /tmp/api_health.json -w 'api /health -> %{http_code}\n' http://localhost:8080/health
curl -s -o /tmp/provider_health.json -w 'provider /health -> %{http_code}\n' http://localhost:8082/health
curl -s -o /dev/null -w 'api /docs -> %{http_code}\n' http://localhost:8080/docs
curl -s -o /dev/null -w 'provider /docs -> %{http_code}\n' http://localhost:8082/docs
```

```bash
# ALLOW
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: smoke-allow-001' \
  -H 'X-Merchant-Id: merchant-smoke-001' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-smoke-001' \
  -d '{"amount":100.00,"currency":"BRL","method":"PIX","destination":"dest-safe-allow-001"}'

# BLOCKED (AML blocklist)
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: smoke-blocked-001' \
  -H 'X-Merchant-Id: merchant-smoke-001' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-smoke-001' \
  -d '{"amount":50.00,"currency":"BRL","method":"PIX","destination":"dest-blocked-001"}'

# IN_REVIEW + approve
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: smoke-review-001' \
  -H 'X-Merchant-Id: merchant-smoke-001' \
  -H 'X-Customer-Id: customer-full-001' \
  -H 'X-Account-Id: account-smoke-001' \
  -d '{"amount":18000.00,"currency":"BRL","method":"TED","destination":"dest-review-001"}'
curl -s -X POST http://localhost:8080/review/136745ba-473e-4aa2-8a75-133d27ad660d/approve

# IN_REVIEW + reject
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: smoke-review-reject-001' \
  -H 'X-Merchant-Id: merchant-smoke-001' \
  -H 'X-Customer-Id: customer-full-001' \
  -H 'X-Account-Id: account-smoke-001' \
  -d '{"amount":18000.00,"currency":"BRL","method":"TED","destination":"dest-review-reject-001"}'
curl -s -X POST http://localhost:8080/review/1da3baa5-7973-4b3a-8d3f-da07e9edafd9/reject

# Idempotency replay
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: smoke-idem-001' \
  -H 'X-Merchant-Id: merchant-smoke-001' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-smoke-001' \
  -d '{"amount":77.00,"currency":"BRL","method":"PIX","destination":"dest-idem-001"}'
```

```bash
# Provider endpoints
curl -s -X POST http://localhost:8082/providers/pix/confirm \
  -H 'Content-Type: application/json' \
  -d '{"payment_id":"11111111-1111-1111-1111-111111111111","merchant_id":"merchant-smoke-001","amount":10.00,"currency":"BRL","method":"PIX"}'

curl -s -X POST http://localhost:8082/providers/boleto/confirm \
  -H 'Content-Type: application/json' \
  -d '{"payment_id":"11111111-1111-1111-1111-111111111111","merchant_id":"merchant-smoke-001","amount":10.00,"currency":"BRL","method":"PIX"}'

curl -s -X POST http://localhost:8082/providers/ted/confirm \
  -H 'Content-Type: application/json' \
  -d '{"payment_id":"11111111-1111-1111-1111-111111111111","merchant_id":"merchant-smoke-001","amount":10.00,"currency":"BRL","method":"PIX"}'

curl -s -X POST http://localhost:8082/providers/card/confirm \
  -H 'Content-Type: application/json' \
  -d '{"payment_id":"11111111-1111-1111-1111-111111111111","merchant_id":"merchant-smoke-001","amount":10.00,"currency":"BRL","method":"PIX"}'
```

### Observed Results

- `payments-api /health` -> `200`
- `provider-mock /health` -> `200`
- `payments-api /docs` -> `200`
- `provider-mock /docs` -> `200`

Control scenarios:

1. ALLOW
   - `payment_id=f395cfec-f535-492e-af72-d8caa8730cf0`
   - response `status=RECEIVED`
2. BLOCKED (AML destination blocklist)
   - `payment_id=b5a0019f-d022-4de0-826e-d6e30b8decb5`
   - response `status=BLOCKED`
   - `aml_decision=BLOCK`
3. IN_REVIEW + APPROVE
   - `payment_id=136745ba-473e-4aa2-8a75-133d27ad660d`
   - create `status=IN_REVIEW`
   - approve `status=RECEIVED`
4. IN_REVIEW + REJECT
   - `payment_id=1da3baa5-7973-4b3a-8d3f-da07e9edafd9`
   - create `status=IN_REVIEW`
   - reject `status=BLOCKED`
   - `last_error=manual_review_rejected`
5. Idempotency replay
   - both responses returned `payment_id=7ef25beb-5390-47e5-89e4-9ead2f041f50`

Provider calls:

- `/providers/pix/confirm` -> `503` (fault injection expected)
- `/providers/boleto/confirm` -> `200`
- `/providers/ted/confirm` -> `200`
- `/providers/card/confirm` -> `200`
- invalid payload -> `422`

Observability:

- Prometheus query returned `payments_api_request_total`
- Grafana API health -> `200`
- Jaeger UI reachable -> `200`

## Previous Runs Summary - 2026-02-08

Historical runs on `2026-02-08` validated the same checklist:

- ALLOW
- BLOCKED (AML)
- IN_REVIEW + approve
- IN_REVIEW + reject
- idempotency replay consistency
- provider endpoint sweep

Representative execution IDs:

- `RUN_ID=1770578764-31108`
- `PASS=5`
- `FAIL=0`

Note:

- Due to deterministic provider fault injection (`5xx`, timeout, partial failure), approved payments can end as `CONFIRMED` or `FAILED` depending on the run profile and workflow stage.

## Authenticated Path Validation - 2026-02-09

Execution purpose:

- Validate `API_AUTH_ENABLED=true` behavior at boundary layer.

Commands used:

```bash
API_AUTH_ENABLED=true API_AUTH_TOKEN=nyx-smoke-token \
  docker compose -f infra/docker/docker-compose.yml up -d --force-recreate payments-api
```

```bash
# no token
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: auth-smoke-001' \
  -H 'X-Merchant-Id: merchant-auth-001' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-auth-001' \
  -d '{"amount":42.00,"currency":"BRL","method":"PIX","destination":"dest-auth-smoke-001"}'

# invalid token
curl -s -X POST http://localhost:8080/payments \
  -H 'Authorization: Bearer wrong-token' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: auth-smoke-002' \
  -H 'X-Merchant-Id: merchant-auth-001' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-auth-001' \
  -d '{"amount":42.00,"currency":"BRL","method":"PIX","destination":"dest-auth-smoke-001"}'

# valid token
curl -s -X POST http://localhost:8080/payments \
  -H 'Authorization: Bearer nyx-smoke-token' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: auth-smoke-003' \
  -H 'X-Merchant-Id: merchant-auth-001' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-auth-001' \
  -d '{"amount":42.00,"currency":"BRL","method":"PIX","destination":"dest-auth-smoke-001"}'
```

Observed results:

- `POST /payments` without token -> `401`, `{"detail":"Missing bearer token"}`
- `POST /payments` with invalid token -> `401`, `{"detail":"Invalid bearer token"}`
- `POST /payments` with valid token -> `202`
  - `payment_id=654a6f77-6bb7-44ac-9b7a-b515206f0fa6`
  - initial `status=IN_REVIEW`
- `GET /payments/{payment_id}` without token -> `401`
- `GET /payments/{payment_id}` with valid token -> `200`
- `POST /review/{payment_id}/approve` without token -> `401`
- `POST /review/{payment_id}/approve` with valid token -> `200`, `status=RECEIVED`

Post-check rollback to default local mode:

```bash
API_AUTH_ENABLED=false API_AUTH_TOKEN= \
  docker compose -f infra/docker/docker-compose.yml up -d --force-recreate payments-api
```
