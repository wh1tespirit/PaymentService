from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from api.core.errors.handlers.all import handle_all_exceptions
from api.core.errors.handlers.app import app_exception_handler
from api.core.errors.handlers.validation import validation_exception_handler
from api.core.openapi import RESPONSES
from api.middlewares.logging.middleware import LoggingMiddleware
from api.routes.docs.router import router as docs_router
from common import settings
from common.errors import AppError

app = FastAPI(
    title=settings.PROJECT_NAME,
    responses=RESPONSES,  # type: ignore
)

app.add_middleware(LoggingMiddleware)

app.exception_handler(RequestValidationError)(validation_exception_handler)
app.exception_handler(AppError)(app_exception_handler)
app.exception_handler(Exception)(handle_all_exceptions)

app.include_router(docs_router)
