import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from api.core.errors.handlers.all import handle_all_exceptions
from api.core.errors.handlers.app import app_exception_handler
from api.core.errors.handlers.validation import validation_exception_handler
from api.core.openapi import RESPONSES
from api.middlewares.logging.middleware import LoggingMiddleware
from api.routes.docs.router import router as docs_router
from api.routes.payments.router import router as payments_router
from common import settings
from common.broker import create_broker, declare_topology
from common.container import Container
from common.errors import AppError
from core.outbox.publisher import make_publisher
from core.outbox.relay import run_relay_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker = create_broker()
    await broker.connect()
    await declare_topology(broker)

    relay_task = asyncio.create_task(run_relay_loop(make_publisher(broker)))
    yield
    relay_task.cancel()
    with suppress(asyncio.CancelledError):
        await relay_task
    await broker.stop()
    await Container.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    responses=RESPONSES,  # type: ignore
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)

app.exception_handler(RequestValidationError)(validation_exception_handler)
app.exception_handler(AppError)(app_exception_handler)
app.exception_handler(Exception)(handle_all_exceptions)

app.include_router(docs_router)
app.include_router(payments_router)
