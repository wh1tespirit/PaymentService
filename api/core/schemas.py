from typing import Any

from common.errors import ApiExceptionCode
from common.pydantic.base import BaseModel


class ApiResponseErr(BaseModel):
    status: str = "ERR"
    code: ApiExceptionCode
    message: str
    data: Any


class ApiResponse:
    @classmethod
    def err(cls, message: str, code: ApiExceptionCode, data: Any):
        return ApiResponseErr(data=data, message=message, code=code)
