import uuid
from datetime import UTC, datetime


def generate_uuid():
    return uuid.uuid4().hex


def now_utc():
    return datetime.now(UTC)
