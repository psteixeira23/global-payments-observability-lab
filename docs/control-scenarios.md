# Reproducible Control Scenarios

This guide provides deterministic test paths for core control behavior.

For deterministic runs, start from a clean state:

```bash
docker compose -f infra/docker/docker-compose.yml down -v
docker compose -f infra/docker/docker-compose.yml up -d --build
```

## Control Pipeline

For `POST /payments`, the flow is:

1. Validate schema and required headers.
2. Load customer.
3. Enforce customer status and KYC by rail.
4. Enforce amount, daily, and velocity limits.
5. Enforce rate limiting by merchant/customer/account.
6. Compute risk decision.
7. Compute AML decision.
8. Persist payment and outbox with final status.

## Scenario 1: ALLOW

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-allow-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-full-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":100.00,"currency":"BRL","method":"PIX","destination":"dest-safe-001"}'
```

Expected:

- synchronous status `RECEIVED`
- asynchronous final status `CONFIRMED` or `FAILED` (provider fault injection is enabled)

## Scenario 2: BLOCKED (AML blocklist)

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-block-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-full-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":50.00,"currency":"BRL","method":"PIX","destination":"dest-blocked-001"}'
```

Expected:

- status `BLOCKED`

## Scenario 3: IN_REVIEW and Approve

Create payment:

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-review-approve-001' \
  -H 'X-Merchant-Id: merchant-2' \
  -H 'X-Customer-Id: customer-full-001' \
  -H 'X-Account-Id: account-2' \
  -d '{"amount":18000.00,"currency":"BRL","method":"TED","destination":"dest-review-approve-001"}'
```

Approve:

```bash
curl -s -X POST http://localhost:8080/review/<payment_id>/approve
```

Expected:

- immediate status `RECEIVED`
- terminal status `CONFIRMED` or `FAILED`

## Scenario 4: IN_REVIEW and Reject

Create payment:

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-review-reject-001' \
  -H 'X-Merchant-Id: merchant-2' \
  -H 'X-Customer-Id: customer-full-001' \
  -H 'X-Account-Id: account-3' \
  -d '{"amount":18000.00,"currency":"BRL","method":"TED","destination":"dest-review-reject-001"}'
```

Reject:

```bash
curl -s -X POST http://localhost:8080/review/<payment_id>/reject
```

Expected:

- status `BLOCKED`
- `last_error=manual_review_rejected`

## Scenario 5: Idempotency Replay

Send the same request twice with the same merchant and idempotency key:

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-replay-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":90.00,"currency":"BRL","method":"PIX","destination":"dest-idem-001"}'
```

Expected:

- same `payment_id`
- same response payload snapshot

## Scenario 6: KYC Denial

```bash
curl -s -X POST http://localhost:8080/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: idem-kyc-001' \
  -H 'X-Merchant-Id: merchant-1' \
  -H 'X-Customer-Id: customer-basic-001' \
  -H 'X-Account-Id: account-1' \
  -d '{"amount":500.00,"currency":"BRL","method":"TED"}'
```

Expected:

- HTTP `403`
- `error.category=kyc_denied`

## Scenario 7: Rate Limiting

```bash
for i in $(seq 1 140); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/payments \
    -H 'Content-Type: application/json' \
    -H "Idempotency-Key: idem-rate-$i" \
    -H 'X-Merchant-Id: merchant-rate' \
    -H 'X-Customer-Id: customer-basic-001' \
    -H 'X-Account-Id: account-rate' \
    -d '{"amount":10.00,"currency":"BRL","method":"PIX","destination":"dest-rate"}'
done
```

Expected:

- eventual HTTP `429`
- `error.category=rate_limited`
