from http import HTTPStatus

from api.core.schemas import ApiResponseErr
from common.errors import ApiExceptionCode

RESPONSES = {
    HTTPStatus.UNPROCESSABLE_ENTITY: {
        "model": ApiResponseErr,
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {
                    "code": ApiExceptionCode.ValidationError.value,
                    "message": "Validation error",
                    "data": None,
                }
            }
        },
    },
    HTTPStatus.BAD_REQUEST: {
        "model": ApiResponseErr,
        "description": "Bad request",
        "content": {
            "application/json": {
                "example": {"code": ApiExceptionCode.BadRequest.value, "message": "Bad request", "data": None}
            }
        },
    },
    HTTPStatus.INTERNAL_SERVER_ERROR: {
        "model": ApiResponseErr,
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {
                    "code": ApiExceptionCode.InternalServerError.value,
                    "message": "Internal server error",
                    "data": None,
                }
            }
        },
    },
}
