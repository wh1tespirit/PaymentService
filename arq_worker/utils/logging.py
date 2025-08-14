from collections.abc import Callable
from functools import wraps

from arq_worker.utils.types import ArqContext


def with_logging(func: Callable):
    @wraps(func)
    async def wrapper(ctx: ArqContext, *args, **kwargs):
        file_logger = ctx["file_logger"]
        file_logger.info(f"Calling {func.__name__} with args: {args} and kwargs: {kwargs}")
        try:
            return await func(ctx, *args, **kwargs)
        except Exception:
            file_logger.exception(f"Exception occurred in {func.__name__}")
            raise

    return wrapper
