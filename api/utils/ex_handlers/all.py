from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from api.translations.base import get_translations_from_header
from api.utils.errors import ExceptionCodes
from api.utils.response import ApiResponse
from common import settings


async def handle_all_exceptions(request: Request, exc: Exception):
    translations = get_translations_from_header(request.headers.get("accept-language", settings.DEFAULT_LOCALE))
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content=ApiResponse.err(
            message=translations.gettext(f"error_{ExceptionCodes.InternalServerError.value}"),
            code=ExceptionCodes.InternalServerError,
            data=str(exc),
        ).md(mode="json"),
    )
