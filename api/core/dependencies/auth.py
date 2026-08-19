from typing import Annotated

from fastapi import Depends
from fastapi.security import APIKeyHeader, APIKeyQuery, HTTPAuthorizationCredentials, HTTPBearer

from common import settings
from common.errors import ApiExceptionCode, AppError

token_security = HTTPBearer(auto_error=False)
TokenSecurityDI = Depends(token_security)
TokenSecurityDIType = Annotated[HTTPAuthorizationCredentials, TokenSecurityDI]

token_query_security = APIKeyQuery(name="token", auto_error=False)
TokenQueryDI = Depends(token_query_security)
TokenQueryDIType = Annotated[str, TokenQueryDI]


async def auth_token_query_di(token: TokenQueryDIType):
    if token != settings.OPENAPI_TOKEN:
        raise AppError(
            message="Invalid token",
            api_code=ApiExceptionCode.PermissionDenied,
        )
    return token


AuthTokenQueryDI = Depends(auth_token_query_di)
AuthTokenQueryDIType = Annotated[str, AuthTokenQueryDI]


api_key_security = APIKeyHeader(name="X-API-Key", auto_error=False)
ApiKeyDI = Depends(api_key_security)
ApiKeyDIType = Annotated[str | None, ApiKeyDI]


async def auth_api_key_di(api_key: ApiKeyDIType):
    if not api_key or api_key != settings.API_KEY:
        raise AppError(
            message="Invalid or missing API key",
            api_code=ApiExceptionCode.PermissionDenied,
        )
    return api_key


AuthApiKeyDI = Depends(auth_api_key_di)
