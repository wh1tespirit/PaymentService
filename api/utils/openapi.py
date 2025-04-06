from http import HTTPStatus

from api.utils.errors import ExceptionCodes
from api.utils.response import ApiResponseErr

RESPONSES = {
    HTTPStatus.UNPROCESSABLE_ENTITY: {
        "model": ApiResponseErr,
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {
                    "code": ExceptionCodes.ValidationError.value,
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
                "example": {"code": ExceptionCodes.BadRequest.value, "message": "Bad request", "data": None}
            }
        },
    },
    HTTPStatus.INTERNAL_SERVER_ERROR: {
        "model": ApiResponseErr,
        "description": "Internal server error",
        "content": {
            "application/json": {
                "example": {
                    "code": ExceptionCodes.InternalServerError.value,
                    "message": "Internal server error",
                    "data": None,
                }
            }
        },
    },
}
