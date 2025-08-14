from datetime import datetime
from enum import StrEnum
from logging import Logger
from typing import TypedDict

from arq import ArqRedis
from dishka import AsyncContainer


class ArqContext(TypedDict):
    redis: ArqRedis
    job_id: str
    job_try: int
    enqueue_time: datetime
    score: int
    console_logger: Logger
    file_logger: Logger
    container: AsyncContainer


class Queues(StrEnum):
    MAIN_QUEUE = "main_queue"
    CRON_QUEUE = "cron_queue"
