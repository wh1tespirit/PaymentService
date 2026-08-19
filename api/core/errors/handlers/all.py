import logging
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from api.core.schemas import ApiResponse
from api.utils.traceback_formatter import TracebackFormatter
from common import settings
from common.errors import ApiExceptionCode
from common.logger import Loggers


async def handle_all_exceptions(request: Request, exc: Exception):
    logger = logging.getLogger(Loggers.API_CONSOLE)
    logger.error(exc)

    data = TracebackFormatter.format_traceback_json(exc) if settings.DEBUG else None
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content=ApiResponse.err(
            message="Internal server error",
            code=ApiExceptionCode.InternalServerError,
            data=data,
        ).md(mode="json"),
    )
