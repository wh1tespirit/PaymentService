from collections.abc import Callable
from functools import wraps

from arq_worker.utils.types import ArqContext
from common.logger import Loggers, ServiceNames, setup_console_logger, setup_file_logger


def with_logging(func: Callable):
    @wraps(func)
    async def wrapper(ctx: ArqContext, *args, **kwargs):
        file_logger = setup_file_logger(Loggers.ARQ_FILE, ServiceNames.ARQ_WORKER, "arq_worker/logs/")
        console_logger = setup_console_logger(Loggers.ARQ_FILE)
        file_logger.info(f"Calling {func.__name__} with args: {args} and kwargs: {kwargs}")
        kwargs["console_logger"] = console_logger
        kwargs["file_logger"] = file_logger
        try:
            return await func(ctx, *args, **kwargs)
        except Exception:
            file_logger.exception(f"Exception occurred in {func.__name__}")
            raise

    return wrapper
