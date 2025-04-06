from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from api.middlewares.logging.middleware import LoggingMiddleware
from api.middlewares.metrics.middleware import MetricMiddleware
from api.routes.metrics.router import router as metrics_router
from api.routes.sample.router import router as sample_router
from api.utils.errors import CustomHTTPError
from api.utils.ex_handlers.all import handle_all_exceptions
from api.utils.ex_handlers.custom import custom_exception_handler
from api.utils.ex_handlers.validation import validation_exception_handler
from api.utils.openapi import RESPONSES
from common import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    responses=RESPONSES,  # type: ignore
)


app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricMiddleware)

app.exception_handler(RequestValidationError)(validation_exception_handler)
app.exception_handler(CustomHTTPError)(custom_exception_handler)
app.exception_handler(Exception)(handle_all_exceptions)

app.include_router(sample_router)
app.include_router(metrics_router)
