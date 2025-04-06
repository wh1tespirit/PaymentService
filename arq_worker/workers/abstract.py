import datetime
from abc import ABC
from collections.abc import Callable, Sequence
from typing import Any

from arq import ArqRedis
from arq.connections import RedisSettings
from arq.cron import CronJob
from arq.typing import SecondsTimedelta, StartupShutdown, WorkerCoroutine
from arq.worker import Function


class AbstractWorker(ABC):
    """Абстрактный класс для упрощения создания новых worker'ов"""

    # docs https://arq-docs.helpmanual.io/#arq.worker.Worker
    functions: Sequence[Function | WorkerCoroutine | Callable]
    queue_name: str | None = "arq:queue"
    cron_jobs: Sequence[CronJob] | None = None
    redis_settings: RedisSettings | None = None
    redis_pool: ArqRedis | None = None
    burst: bool = False
    on_startup: StartupShutdown | None = None
    on_shutdown: StartupShutdown | None = None
    on_job_start: StartupShutdown | None = None
    on_job_end: StartupShutdown | None = None
    after_job_end: StartupShutdown | None = None
    handle_signals: bool = True
    job_completion_wait: int = 0
    max_jobs: int = 10
    job_timeout: SecondsTimedelta = 300
    keep_result: SecondsTimedelta = 3600
    keep_result_forever: bool = False
    poll_delay: SecondsTimedelta = 0.5
    queue_read_limit: int | None = None
    max_tries: int = 5
    health_check_interval: SecondsTimedelta = 3600
    health_check_key: str | None = None
    ctx: dict[Any, Any] | None = None
    retry_jobs: bool = True
    allow_abort_jobs: bool = False
    max_burst_jobs: int = -1
    job_serializer: Callable[[dict[str, Any]], bytes] | None = None
    job_deserializer: Callable[[bytes], dict[str, Any]] | None = None
    expires_extra_ms: int = 86400000
    timezone: datetime.timezone | None = None
    log_results: bool = True
