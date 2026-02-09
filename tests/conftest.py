from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATHS = [
    ROOT,
    ROOT / "services" / "payments-api",
    ROOT / "services" / "payments-processor",
    ROOT / "services" / "provider-mock",
]

for path in SERVICE_PATHS:
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

os.environ.setdefault("OTEL_TRACES_EXPORTER", "none")
os.environ.setdefault("OTEL_METRICS_EXPORTER", "none")
