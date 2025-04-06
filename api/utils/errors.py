from enum import Enum
from http import HTTPStatus
from typing import Any


class ExceptionCodes(Enum):
    InternalServerError = 1
    BadRequest = 2
    ValidationError = 3
    PermissionDenied = 4
    ObjectNotFound = 5
    ObjectAlreadyExists = 6


class CustomHTTPError(Exception):
    def __init__(self, code: ExceptionCodes, data: Any = None):
        self.code = code
        self.status_code = HTTPStatus.BAD_REQUEST
        self.data = data
