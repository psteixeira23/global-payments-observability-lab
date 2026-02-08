# Smoke Test Evidence - 2026-02-08

Environment:

- docker compose stack running locally
- Redis and transactional tables reset before execution

Command objective:

- validate ALLOW, BLOCKED, IN_REVIEW approve/reject, and idempotency replay

Execution summary:

- `RUN_ID=1770578764-31108`
- `PASS=5`
- `FAIL=0`

Observed results:

1. ALLOW
   - `payment_id=37802969-f4aa-49dc-a51e-26ff7cf7e4bf`
   - terminal status: `CONFIRMED`
2. BLOCKED (AML destination blocklist)
   - `payment_id=d26e996b-530a-4246-b232-1cd5ef8e166e`
   - status: `BLOCKED`
3. IN_REVIEW + APPROVE
   - `payment_id=4ecda970-a083-4f46-a64e-a0276b061463`
   - terminal status: `CONFIRMED`
4. IN_REVIEW + REJECT
   - `payment_id=49d19a12-95a7-46e7-87b0-5aca58253db6`
   - status: `BLOCKED`
   - `last_error=manual_review_rejected`
5. Idempotency replay
   - `payment_id=b0717b73-eb7d-40d4-9a9a-9dfda3de15eb`
   - repeated call returned same payload snapshot

Notes:

- Due to provider fault injection (`5xx`, timeout, partial failures), approved payments may terminate in `CONFIRMED` or `FAILED`. This is expected behavior.

## Re-Run (Observability Profile Enabled)

Executed with local Jaeger/Prometheus/Grafana profile enabled.

Observed checklist:

1. ALLOW
   - `payment_id=87330642-67fe-452b-8b52-ea83afae06d8`
   - terminal status: `CONFIRMED`
2. BLOCKED
   - `payment_id=5a1823b5-feb9-45c0-bcae-176c3bfb082b`
   - status: `BLOCKED`
3. IN_REVIEW + APPROVE
   - `payment_id=0fe5019c-4e35-4682-82a0-56c3dad61184`
   - terminal status: `CONFIRMED`
4. IN_REVIEW + REJECT
   - `payment_id=c8b17166-4152-4412-90fc-c8ab6d8ad0be`
   - status: `BLOCKED`
   - `last_error=manual_review_rejected`
5. IDEMPOTENCY REPLAY
   - `payment_id=d0e93858-bb92-4a63-957a-d688ea123de7`
   - repeated call returned same payload snapshot

## Re-Run (Full Endpoint Sweep)

Execution date: `2026-02-08`

Validated endpoints:

- `GET /health` (payments-api)
- `POST /payments`
- `GET /payments/{payment_id}`
- `POST /review/{payment_id}/approve`
- `POST /review/{payment_id}/reject`
- `GET /health` (provider-mock)
- `POST /providers/pix/confirm`
- `POST /providers/boleto/confirm`
- `POST /providers/ted/confirm`
- `POST /providers/card/confirm`

Observed results:

1. ALLOW
   - `payment_id=892766f7-a958-40c7-86e8-5a4a8bde98fe`
   - `status=RECEIVED`
2. IN_REVIEW + APPROVE
   - `payment_id=a3c24a6f-89b9-4d4c-bc3c-aa1a9b49962f`
   - review response `status=RECEIVED`
3. IN_REVIEW + REJECT
   - `payment_id=fb016ed9-b5f8-4a0b-bea0-dcb97f61fdf2`
   - review response `status=BLOCKED`
   - `last_error=manual_review_rejected`
4. BLOCKED
   - `payment_id=a51cbea0-8a29-4d37-8568-c30a12062bb5`
   - `aml_decision=BLOCK`
5. IDEMPOTENCY REPLAY
   - first/second response returned same `payment_id=03f58a09-71f9-4584-9ba9-69b5dd0773c5`
6. Provider mock calls
   - `pix`: returned `503` (fault injection expected)
   - `boleto`, `ted`, `card`: returned `200` with provider payload

Important note:

- A first attempt to generate `IN_REVIEW` with `customer-basic-001` and high PIX amount returned `limit_exceeded` due accumulated daily usage in persistent local volume. This is expected for long-lived environments.
