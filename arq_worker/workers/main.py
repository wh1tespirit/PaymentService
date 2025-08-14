from arq_worker.settings import REDIS_SETTINGS
from arq_worker.tasks.sample import sample_task
from arq_worker.utils.handlers import on_job_end, on_job_start, on_startup
from arq_worker.utils.types import Queues
from arq_worker.workers.abstract import AbstractWorker


class MainWorker(AbstractWorker):
    functions = (sample_task,)
    redis_settings = REDIS_SETTINGS
    queue_name = Queues.MAIN_QUEUE
    on_startup = on_startup
    on_job_start = on_job_start
    on_job_end = on_job_end
