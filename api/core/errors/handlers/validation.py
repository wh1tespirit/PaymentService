from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.core.schemas import ApiResponse
from common.errors import ApiExceptionCode


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content=ApiResponse.err(
            message="Validation error",
            code=ApiExceptionCode.ValidationError,
            data=exc.errors(),
        ).md(mode="json"),
    )
