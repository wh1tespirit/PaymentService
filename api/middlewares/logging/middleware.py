import json
import time
import traceback
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse, StreamingResponse
from starlette.types import ASGIApp

from api.middlewares.logging.models import FileLogs, RequestLogs
from common.logger import Loggers, ServiceNames, setup_console_logger, setup_file_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.file_logger = setup_file_logger(Loggers.API_FILE, ServiceNames.API, "api/logs/")
        self.console_logger = setup_console_logger(Loggers.API_CONSOLE)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        logs = FileLogs(
            nginx_request_id=request.headers.get("X-Request-Id"),
            request=RequestLogs(
                method=request.method,
                url=str(request.url.path),
                path_params=request.path_params,
                query_params=dict(request.query_params),
                headers=dict(request.headers),
                cookies=request.cookies,
            ),
        )

        if request.headers.get("Content-Type") == "application/json":
            try:
                logs.request.data = json.loads(await request.body())
            except Exception:
                logs.request.data = {}
        try:
            response: StreamingResponse = await call_next(request)
            logs.response.headers = dict(response.headers)
            logs.response.status_code = response.status_code

            body = b""

            async for chunk in response.body_iterator:
                body += chunk if isinstance(chunk, bytes) else chunk.encode()

            if response.headers.get("Content-Type") == "application/json":
                logs.response.data = json.loads(body)
            else:
                logs.response.data = body.decode()

            return StarletteResponse(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        except Exception as e:
            logs.traceback = traceback.format_exc()
            logs.exception = str(e)
            raise

        finally:
            logs.timedelta = round(time.time() - start_time, 3)
            self.file_logger.info(None, logs.md())
