from pathlib import Path

from prometheus_client import CollectorRegistry, Counter, Histogram
from prometheus_client.multiprocess import MultiProcessCollector

from common import settings

REGISTRY = CollectorRegistry()

if settings.PROMETHEUS_MULTIPROC_DIR:
    path = Path(settings.PROMETHEUS_MULTIPROC_DIR).mkdir(parents=True, exist_ok=True)

MultiProcessCollector(REGISTRY, path=settings.PROMETHEUS_MULTIPROC_DIR)


REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency",
    labelnames=["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, "+Inf"),
    registry=REGISTRY,
)
RESPONSES = Counter(
    "responses",
    "Responses",
    labelnames=["request_method", "request_path", "response_status_code"],
    registry=REGISTRY,
)
