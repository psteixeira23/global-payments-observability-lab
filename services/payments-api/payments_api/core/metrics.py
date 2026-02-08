from __future__ import annotations

from opentelemetry import metrics

meter = metrics.get_meter("payments-api")
request_counter = meter.create_counter("payments_api_request_total", description="Total requests")
error_counter = meter.create_counter(
    "payments_api_error_total", description="Total error responses"
)
latency_histogram = meter.create_histogram(
    "payments_api_request_latency_ms", description="Request latency in ms"
)

kyc_check_duration = meter.create_histogram(
    "kyc_check_duration", description="KYC check duration in ms"
)
kyc_denied_total = meter.create_counter("kyc_denied_total", description="Rejected by KYC controls")

limits_check_duration = meter.create_histogram(
    "limits_check_duration", description="Limits check duration in ms"
)
limits_exceeded_total = meter.create_counter(
    "limits_exceeded_total", description="Rejected by limits"
)

rate_limited_total = meter.create_counter("rate_limited_total", description="Rate-limited requests")

risk_decisions_total = meter.create_counter(
    "risk_decisions_total", description="Risk decision count"
)
aml_decisions_total = meter.create_counter("aml_decisions_total", description="AML decision count")

review_queue_size = meter.create_histogram(
    "review_queue_size", description="Current review queue size snapshots"
)
idempotency_replay_total = meter.create_counter(
    "idempotency_replay_total", description="Idempotent replay count"
)
