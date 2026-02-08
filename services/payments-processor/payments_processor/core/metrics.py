from __future__ import annotations

from opentelemetry import metrics

meter = metrics.get_meter("payments-processor")
outbox_backlog = meter.create_histogram(
    "payments_processor_outbox_backlog", description="Outbox backlog size snapshots"
)
outbox_lag_seconds = meter.create_histogram(
    "payments_processor_outbox_lag_seconds", description="Outbox processing lag"
)
provider_latency = meter.create_histogram(
    "payments_processor_provider_latency_ms", description="Provider call latency"
)
provider_errors = meter.create_counter(
    "payments_processor_provider_errors", description="Provider call errors"
)
