from typing import Any

from common.errors import ApiExceptionCode
from common.pydantic.base import BaseModel


class ApiResponseOk[T](BaseModel):
    status: str = "OK"
    code: int = 0
    message: str = ""
    data: T


class ApiResponseErr(BaseModel):
    status: str = "ERR"
    code: ApiExceptionCode
    message: str
    data: Any


class ApiResponse:
    @classmethod
    def ok[T](cls, data: T) -> ApiResponseOk[T]:
        return ApiResponseOk[type(data)](data=data)

    @classmethod
    def err(cls, message: str, code: ApiExceptionCode, data: Any):
        return ApiResponseErr(data=data, message=message, code=code)
