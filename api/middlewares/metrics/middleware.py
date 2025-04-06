from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from api.services.metric.service import MetricService


class MetricMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        metric_service = MetricService()

        async with metric_service.latency(request.method, request.url.path):
            response: StreamingResponse = await call_next(request)
            metric_service.response_count(request.method, request.url.path, response.status_code)

        return response
