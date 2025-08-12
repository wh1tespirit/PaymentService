from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from common import settings
from common.translations.base import get_locale_from_header
from common.translations.enums import APIDomains, Scopes
from common.translations.service import TranslationService


class TranslationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        locale = get_locale_from_header(request.headers.get("Accept-Language", settings.DEFAULT_LOCALE))
        translation = TranslationService(
            scope=Scopes.API,
            domains=[APIDomains.ERRORS],
            locale=locale,
        )
        request.state.translation = translation
        return await call_next(request)
