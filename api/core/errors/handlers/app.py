import logging
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from api.core.schemas import ApiResponse
from common.errors import ApiExceptionCode, AppError
from common.logger import Loggers
from common.translations.enums import APIDomains
from common.translations.service import TranslationService


async def app_exception_handler(request: Request, exc: AppError):
    logger = logging.getLogger(Loggers.API_CONSOLE)
    logger.error(exc)

    translation: TranslationService = request.state.translation
    if exc.api_code:
        api_code = exc.api_code
        status = HTTPStatus.BAD_REQUEST
        message = translation.get_translation(APIDomains.ERRORS, f"error_{api_code.value}")
    else:
        api_code = ApiExceptionCode.InternalServerError
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        message = translation.get_translation(APIDomains.ERRORS, "error_1")
    content = ApiResponse.err(message=message, code=api_code, data=exc.api_data)
    return JSONResponse(status_code=status, content=content.md(mode="json"))
