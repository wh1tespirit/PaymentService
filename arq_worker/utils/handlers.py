import logging

from common.container import Container
from common.logger import Loggers, ServiceNames, setup_console_logger, setup_file_logger


async def on_startup(ctx: dict):
    setup_file_logger(Loggers.ARQ_FILE, ServiceNames.ARQ_WORKER, "arq_worker/logs/")
    setup_console_logger(Loggers.ARQ_CONSOLE)


async def on_job_start(ctx: dict):
    wrapper = Container()
    ctx["container"] = wrapper.container
    ctx["console_logger"] = logging.getLogger(Loggers.ARQ_CONSOLE)
    ctx["file_logger"] = logging.getLogger(Loggers.ARQ_FILE)


async def on_job_end(ctx: dict, *args, **kwargs):
    await ctx["container"].close()
