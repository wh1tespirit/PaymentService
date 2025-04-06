from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from arq.jobs import Job

from common import settings

REDIS_SETTINGS = RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD)


class ArqWorker:
    pool: ArqRedis
    redis_settings: RedisSettings

    def __init__(self):
        self.redis_settings = REDIS_SETTINGS

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.pool.close()

    async def connect(self):
        self.pool = await create_pool(self.redis_settings)

    async def disconnect(self):
        await self.pool.close()

    async def add_job(
        self,
        function: Callable,
        job_id: str | None = None,
        queue_name: str | None = None,
        defer_until: datetime | None = None,
        defer_by: None | float | timedelta = None,
        expires: None | float | timedelta = None,
        job_try: int | None = None,
        **kwargs: Any,
    ):
        return await self.pool.enqueue_job(
            function=function.__name__,
            _job_id=job_id,
            _queue_name=queue_name,
            _defer_until=defer_until,
            _defer_by=defer_by,
            _expires=expires,
            _job_try=job_try,
            **kwargs,
        )

    async def abort_job(self, job_id: str):
        job = Job(job_id=job_id, redis=self.pool)
        await job.abort()

    async def get_job(self, job_id: str):
        job = Job(job_id=job_id, redis=self.pool)
        return job
