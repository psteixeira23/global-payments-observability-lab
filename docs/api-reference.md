# API Reference

## Payments API (`:8080`)

### POST `/payments`

Required headers:

- `Idempotency-Key`
- `X-Merchant-Id`
- `X-Customer-Id`
- `X-Account-Id`

Body:

- `amount` (decimal, `> 0`)
- `currency` (3-char code)
- `method` (`PIX|BOLETO|TED|CARD`)
- `destination` (optional)
- `metadata` (optional object)

Success response (`202`):

- `payment_id`
- `status`
- `trace_id`
- `risk_decision`
- `aml_decision`

### GET `/payments/{payment_id}`

Returns:

- identifiers (`payment_id`, `merchant_id`, `customer_id`, `account_id`)
- payment details (`amount`, `currency`, `method`, `status`)
- risk/AML fields
- `created_at`, `updated_at`, `last_error`

### POST `/review/{payment_id}/approve`

Behavior:

- only valid when current status is `IN_REVIEW`
- transitions payment to `RECEIVED`
- enqueues `PaymentRequested` for async processor

### POST `/review/{payment_id}/reject`

Behavior:

- only valid when current status is `IN_REVIEW`
- transitions payment to `BLOCKED`
- persists `manual_review_rejected` in `last_error`

## Provider Mock API (`:8082`)

Endpoints:

- POST `/providers/pix/confirm`
- POST `/providers/boleto/confirm`
- POST `/providers/ted/confirm`
- POST `/providers/card/confirm`

Possible errors:

- `503` provider unavailable
- `504` provider timeout

## Payment Statuses

- `RECEIVED`
- `VALIDATED`
- `IN_REVIEW`
- `PROCESSING`
- `CONFIRMED`
- `FAILED`
- `BLOCKED`

## Error Categories

Standard envelope:

```json
{
  "error": {
    "category": "validation_error",
    "message": "..."
  }
}
```

Main categories:

- `validation_error`
- `idempotency_conflict`
- `concurrency_conflict`
- `kyc_denied`
- `limit_exceeded`
- `rate_limited`
- `unexpected`
