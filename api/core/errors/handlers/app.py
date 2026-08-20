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
    ApiExceptionCode.Conflict: HTTPStatus.CONFLICT,
}


async def app_exception_handler(request: Request, exc: AppError):
    logger = logging.getLogger(Loggers.API_CONSOLE)
    logger.error(exc)

    api_code = exc.api_code or ApiExceptionCode.InternalServerError
    content = ApiResponse.err(message=exc.message, code=api_code, data=exc.api_data)
    # .get, а не [], чтобы новый код в enum не ронял сам обработчик ошибок.
    status = STATUS_BY_CODE.get(api_code, HTTPStatus.INTERNAL_SERVER_ERROR)
    return JSONResponse(status_code=status, content=content.md(mode="json"))
