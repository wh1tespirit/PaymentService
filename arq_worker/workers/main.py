from arq_worker.main import REDIS_SETTINGS
from arq_worker.tasks.sample import sample_task
from arq_worker.utils.mongo import mongo_shutdown_handler, mongo_startup_handler
from arq_worker.utils.types import Queues
from arq_worker.workers.abstract import AbstractWorker


class MainWorker(AbstractWorker):
    functions = (sample_task,)
    redis_settings = REDIS_SETTINGS
    queue_name = Queues.SAMPLE_QUEUE
    on_job_start = mongo_startup_handler
    on_job_end = mongo_shutdown_handler
