from enum import StrEnum


class Scopes(StrEnum):
    API = "api"


class APIDomains(StrEnum):
    MESSAGES = "messages"
    ERRORS = "errors"


class Locale(StrEnum):
    EN = "en"
    RU = "ru"
