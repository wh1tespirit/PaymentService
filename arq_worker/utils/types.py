from datetime import datetime
from enum import StrEnum
from logging import Logger
from typing import TypedDict

from arq import ArqRedis

from common.mongo.client import MongoClient


class ArqContext(TypedDict):
    redis: ArqRedis
    job_id: str
    job_try: int
    enqueue_time: datetime
    score: int


class ArqLoggerContext(ArqContext):
    console_logger: Logger
    file_logger: Logger


class MongoArqContext(ArqLoggerContext):
    mongo: MongoClient


class Queues(StrEnum):
    SAMPLE_QUEUE = "sample_queue"
