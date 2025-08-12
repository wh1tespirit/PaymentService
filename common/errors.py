from enum import Enum
from typing import Any


class ApiExceptionCode(Enum):
    InternalServerError = 1
    BadRequest = 2
    ValidationError = 3
    PermissionDenied = 4
    ObjectNotFound = 5


class AppError(Exception):
    def __init__(
        self,
        message: str,
        data: Any | None = None,
        api_code: ApiExceptionCode | None = None,
        api_data: Any | None = None,
    ):
        self.message = message
        self.data = data
        self.api_code = api_code
        self.api_data = api_data

    def __str__(self):
        message = f"Message: {self.message}\n"
        if self.data:
            message += f"Data: {self.data}\n"
        if self.api_code:
            message += f"API code: {self.api_code}\n"
        if self.api_data:
            message += f"API data: {self.api_data}"
        return message

    def __dict__(self):
        return {
            "message": self.message,
            "data": self.data,
            "api_code": self.api_code,
            "api_data": self.api_data,
        }
