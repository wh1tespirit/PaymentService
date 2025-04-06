from contextlib import asynccontextmanager

from api.services.metric.registry import REQUEST_LATENCY, RESPONSES


class MetricService:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @staticmethod
    @asynccontextmanager
    async def latency(method: str, url: str):
        with REQUEST_LATENCY.labels(method, url).time():
            yield

    @staticmethod
    def response_count(request_method: str, request_path: str, response_status_code: int):
        RESPONSES.labels(request_method, request_path, response_status_code).inc()
