import secrets
from datetime import datetime

import pytz
from bson import ObjectId


def generate_object_id():
    return str(ObjectId())


def generate_token(nbytes: int):
    return secrets.token_hex(nbytes)


def get_moscow_time() -> str:
    return str(datetime.now(pytz.timezone("Europe/Moscow")))


def get_moscow_time_in_datetime() -> datetime:
    return datetime.now(pytz.timezone("Europe/Moscow"))


def get_utc_datetime() -> datetime:
    return datetime.now(pytz.utc)
