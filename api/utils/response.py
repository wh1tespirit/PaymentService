from typing import Any

from api.utils.errors import ExceptionCodes
from common.pydantic.base import BaseModel


class ApiResponseOk[T](BaseModel):
    status: str = "OK"
    code: int = 0
    message: str = ""
    data: T


class ApiResponseErr(BaseModel):
    status: str = "ERR"
    code: ExceptionCodes
    message: str
    data: Any


class ApiResponse:
    @classmethod
    def ok(cls, data: Any):
        return ApiResponseOk[type(data)](data=data)

    @classmethod
    def err(cls, message: str, code: ExceptionCodes, data: Any):
        return ApiResponseErr(data=data, message=message, code=code)
