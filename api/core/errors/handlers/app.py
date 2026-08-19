import logging
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from api.core.schemas import ApiResponse
from common.errors import ApiExceptionCode, AppError
from common.logger import Loggers

STATUS_BY_CODE = {
    ApiExceptionCode.InternalServerError: HTTPStatus.INTERNAL_SERVER_ERROR,
    ApiExceptionCode.BadRequest: HTTPStatus.BAD_REQUEST,
    ApiExceptionCode.ValidationError: HTTPStatus.UNPROCESSABLE_ENTITY,
    ApiExceptionCode.PermissionDenied: HTTPStatus.UNAUTHORIZED,
    ApiExceptionCode.ObjectNotFound: HTTPStatus.NOT_FOUND,
}


async def app_exception_handler(request: Request, exc: AppError):
    logger = logging.getLogger(Loggers.API_CONSOLE)
    logger.error(exc)

    api_code = exc.api_code or ApiExceptionCode.InternalServerError
    content = ApiResponse.err(message=exc.message, code=api_code, data=exc.api_data)
    return JSONResponse(status_code=STATUS_BY_CODE[api_code], content=content.md(mode="json"))
