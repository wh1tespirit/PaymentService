import math
from datetime import datetime
from typing import Any

from pydantic import Field

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


class TokenResp(BaseModel):
    token: str = Field(description="Токен пользователя")
    exp: datetime | None = Field(default=None, description="Время истечения токена")


class PaginatorReq(BaseModel):
    limit: int = Field(default=10, description="Количество элементов на странице")
    offset: int = Field(default=0, description="Сдвиг")


class PaginatorResp[T](BaseModel):
    page: int
    total_pages: int
    items: list[T]

    @classmethod
    def response(cls, items: list[T], total: int, limit: int, offset: int):
        return cls(
            page=offset // limit + 1,
            total_pages=math.ceil(total / limit),
            items=items,
        )
