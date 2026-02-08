# Week 2 Roadmap

Planned expansion items:

1. Add queue adapter (Kafka or RabbitMQ) for review and event fan-out.
2. Add approval SLA monitoring for `IN_REVIEW` payments.
3. Add schema migration workflow with Alembic.
4. Expand AML scenarios (including synthetic rapid in-out behavior).
5. Add executable load-test scripts in `scripts/loadtest`.
6. Add local OTel collector and dashboard stack while keeping external SaaS optional.

## Load Test Plan

Target tools:

- `k6`
- `locust`

Initial scenarios:

- high concurrency with repeated idempotency keys
- boundary pressure on rate limits
- risk/AML decision distribution under mixed traffic
- outbox backlog and processor lag under provider fault injection
