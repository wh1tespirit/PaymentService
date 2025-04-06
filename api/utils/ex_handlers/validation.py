from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.translations.base import get_translations_from_header
from api.utils.errors import ExceptionCodes
from api.utils.response import ApiResponse
from common import settings


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    translations = get_translations_from_header(request.headers.get("accept-language", settings.DEFAULT_LOCALE))
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content=ApiResponse.err(
            message=translations.gettext(f"error_{ExceptionCodes.ValidationError}"),
            code=ExceptionCodes.ValidationError,
            data=exc.errors(),
        ).md(mode="json"),
    )
