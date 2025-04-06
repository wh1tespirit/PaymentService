from enum import StrEnum
from typing import Any

from pydantic import Field

from common.pydantic.base import BaseModel


class Level(StrEnum):
    OK = "OK"
    ERROR = "ERROR"


class RequestLogs(BaseModel):
    method: str
    url: str
    path_params: dict[str, str]
    query_params: dict[str, str]
    headers: dict[str, str]
    cookies: dict[str, str]
    json_body: Any | None = None


class ResponseLogs(BaseModel):
    status_code: int | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any | None = None


class FileLogs(BaseModel):
    level: Level
    date: str
    project_name: str
    service_name: str
    request: RequestLogs
    response: ResponseLogs = Field(default_factory=ResponseLogs)
    timedelta: float = 0
    nginx_request_id: str | None = None
    traceback: str | None = None
    exception: str | None = None
