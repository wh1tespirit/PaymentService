from fastapi import Request
from fastapi.responses import JSONResponse

from api.translations.base import get_translations_from_header
from api.utils.errors import CustomHTTPError
from api.utils.response import ApiResponse
from common import settings


async def custom_exception_handler(request: Request, exc: CustomHTTPError):
    translations = get_translations_from_header(request.headers.get("accept-language", settings.DEFAULT_LOCALE))
    content = ApiResponse.err(message=translations.gettext(f"error_{exc.code.value}"), code=exc.code, data=exc.data)
    return JSONResponse(status_code=exc.status_code, content=content.md(mode="json"))
