import json
import time
import traceback
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse, StreamingResponse
from starlette.types import ASGIApp

from api.middlewares.logging.models import FileLogs, Level, RequestLogs
from common import settings
from common.logger import Loggers, ServiceNames, setup_console_logger, setup_file_logger
from common.utils import get_moscow_time


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.file_logger = setup_file_logger(Loggers.API_FILE, ServiceNames.API, "api/logs/")
        self.console_logger = setup_console_logger(Loggers.API_CONSOLE)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        logs = FileLogs(
            level=Level.OK,
            date=get_moscow_time(),
            project_name=settings.PROJECT_NAME,
            service_name="API",
            nginx_request_id=request.headers.get("X-Request-Id"),
            request=RequestLogs(
                method=request.method,
                url=str(request.url.path),
                path_params=request.path_params,
                query_params=request.query_params,
                headers=request.headers,
                cookies=request.cookies,
            ),
        )

        if request.headers.get("Content-Type") == "application/json":
            logs.request.json_body = json.loads(await request.body())

        try:
            response: StreamingResponse = await call_next(request)
            logs.response.headers = dict(response.headers)
            logs.response.status_code = response.status_code

            body = b""

            async for chunk in response.body_iterator:
                body += chunk if isinstance(chunk, bytes) else chunk.encode()

            if response.headers.get("Content-Type") == "application/json":
                logs.response.body = json.loads(body)
            else:
                logs.response.body = body.decode()

            return StarletteResponse(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        except Exception as e:
            logs.level = Level.ERROR
            logs.traceback = traceback.format_exc()
            logs.exception = str(e)
            raise

        finally:
            logs.timedelta = round(time.time() - start_time, 3)
            self.file_logger.info(logs.md_json())
