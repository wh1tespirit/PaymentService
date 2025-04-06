from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from api.utils.errors import CustomHTTPError, ExceptionCodes
from common import settings

headers_token_security = APIKeyHeader(name="Authorization", auto_error=False)


async def get_headers_token_di(token: Annotated[str, Security(headers_token_security)]):
    if not token:
        raise CustomHTTPError(ExceptionCodes.PermissionDenied)
    return token


async def is_admin_di(token: Annotated[str, Depends(get_headers_token_di)]):
    if token != settings.SOME_ADMIN_TOKEN:
        raise CustomHTTPError(ExceptionCodes.PermissionDenied)
    return token
