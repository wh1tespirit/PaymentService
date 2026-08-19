from enum import StrEnum


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
