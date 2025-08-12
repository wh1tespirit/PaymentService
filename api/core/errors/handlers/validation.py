from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.core.schemas import ApiResponse
from common.errors import ApiExceptionCode
from common.translations.enums import APIDomains
from common.translations.service import TranslationService


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    translation: TranslationService = request.state.translation
    key = f"error_{ApiExceptionCode.ValidationError.value}"
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content=ApiResponse.err(
            message=translation.get_translation(APIDomains.ERRORS, key),
            code=ApiExceptionCode.ValidationError,
            data=exc.errors(),
        ).md(mode="json"),
    )
