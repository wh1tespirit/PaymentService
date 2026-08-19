# Payment Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Асинхронный сервис процессинга платежей: API создаёт платежи через Outbox pattern, FastStream-консюмер эмулирует шлюз, шлёт webhook, с retry (2с/4с/8с) и DLQ.

**Architecture:** Слоистая структура существующего шаблона (роут → контроллер → use case в `core/`, DI через dishka). Outbox-relay — фоновая asyncio-задача в процессе api. Consumer — отдельное FastStream-приложение (пакет `consumer/`). Retry — очереди с TTL + dead-letter-exchange, без плагинов.

**Tech Stack:** FastAPI + Pydantic v2, SQLAlchemy 2.0 async + asyncpg, PostgreSQL, RabbitMQ + FastStream, Alembic, dishka, uv, pytest + pytest-asyncio, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-19-payment-service-design.md` — план аргументирует от неё; исполнитель читает обе.

## Global Constraints

- Python `>=3.12` (из pyproject; локально ставится через uv, `uv sync` сам скачает интерпретатор).
- docker-compose: ровно 4 сервиса — `postgres`, `rabbitmq`, `api`, `consumer`. Никаких пятых сервисов.
- Зависимости добавлять ТОЛЬКО перечисленные в Task 1. Ничего сверх.
- Имена очередей/обменника фиксированы: exchange `payments` (direct, durable), очередь `payments.new`, retry-очереди `payments.new.retry.1/2/3` (TTL 2000/4000/8000 мс), DLQ `payments.new.dlq`.
- Семантика попыток: заголовок `x-attempt` = число уже сделанных ретраев (0 при первой доставке). Ошибка при `x-attempt >= 3` → DLQ. Итого: первичная доставка + 3 ретрая.
- Эндпоинты: `POST /api/v1/payments` (заголовки `X-API-Key`, `Idempotency-Key`; ответ 202 `{payment_id, status, created_at}`), `GET /api/v1/payments/{payment_id}`. Ошибки — в конверте шаблона `{"status": "ERR", "code": ..., "message": ..., "data": ...}`; успешные ответы — плоские (без конверта `ApiResponse.ok`), строго по форме из ТЗ.
- Env-переменные: `API_KEY`, `RABBITMQ_URI`, `DATABASE_URI`, `WEBHOOK_TIMEOUT`, `OUTBOX_POLL_INTERVAL`, `OUTBOX_BATCH_SIZE`, `PROJECT_NAME`, `OPENAPI_TOKEN`.
- Каждая задача заканчивается: `uv run pytest` зелёный (когда тесты уже есть), `uv run ruff check .` чистый, отдельный commit.
- Коммиты — от имени текущего git-пользователя, без Co-Authored-By.
- Локальные команды: uv ставится в `~/.local/bin` — если команда `uv` не находится, использовать `~/.local/bin/uv`.

---

### Task 1: Инструменты и зависимости

**Files:**
- Modify: `pyproject.toml` (блоки `dependencies`, новый `[dependency-groups]`)

**Interfaces:**
- Produces: рабочий `uv run python`, установленные `faststream[rabbit]`, `httpx`, dev-группа `pytest`, `pytest-asyncio`, `ruff`.

- [ ] **Step 1: Установить uv (если нет)**

```bash
command -v uv || command -v ~/.local/bin/uv || curl -LsSf https://astral.sh/uv/install.sh | sh
```

- [ ] **Step 2: Обновить зависимости в pyproject.toml**

Заменить блок `dependencies` (удалены `arq`, `babel`, `prometheus-client`, `python-multipart`, `pytz`, `watchdog` — по grep нигде в коде не используются; добавлены `faststream[rabbit]`, `httpx`):

```toml
dependencies = [
    "alembic>=1.16.4",
    "asyncpg>=0.30.0",
    "dishka>=1.6.0",
    "dotenv>=0.9.9",
    "fastapi>=0.115.12",
    "faststream[rabbit]>=0.6,<0.8",
    "greenlet>=3.2.4",
    "httpx>=0.28",
    "pydantic>=2.11.1",
    "scalar-fastapi>=1.2.3",
    "sqlalchemy>=2.0.43",
    "uvicorn>=0.34.0",
]
```

После секции `[project]` добавить:

```toml
[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=1.0",
    "ruff>=0.8",
]
```

- [ ] **Step 3: Синхронизировать окружение**

```bash
uv sync
```

Expected: создан `.venv` с Python 3.12+, uv.lock обновлён без ошибок резолва.

- [ ] **Step 4: Проверить импорты**

```bash
uv run python -c "import faststream, httpx; print(faststream.__version__)"
```

Expected: печатает версию 0.6.x или 0.7.x. Если API FastStream в установленной версии отличается от используемого в задачах 7–10 (`broker.stop()` vs `broker.close()`), адаптировать по установленной версии.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: replace arq/babel/prometheus deps with faststream and httpx"
```

---

### Task 2: Чистка шаблона

Удаляем всё, чего нет в ТЗ, и упрощаем то, что от этого зависит. После задачи приложение должно импортироваться.

**Files:**
- Delete: `arq_worker/` (весь), `core/arq/`, `core/sample/`, `api/routes/samples/`, `common/translations/`, `api/middlewares/translations/`, `api/configs/`, `common/certs/`, `common/dockerimages/filebeat.Dockerfile`, `api/filebeat.yml`, `api/prometheus.yml`, `api/docker-compose.yml`, `babel.cfg`, `Makefile` (новый будет в Task 3)
- Modify: `api/asgi.py`, `api/core/errors/handlers/app.py`, `api/core/errors/handlers/all.py`, `api/core/errors/handlers/validation.py`, `api/core/schemas.py`, `api/core/enums.py`, `common/settings.py`, `common/logger.py`, `envs/test.env`, `envs/prod.env`

**Interfaces:**
- Produces: `from api.asgi import app` работает; `common.settings` содержит `API_KEY`, `RABBITMQ_URI`, `WEBHOOK_TIMEOUT: float`, `OUTBOX_POLL_INTERVAL: float`, `OUTBOX_BATCH_SIZE: int`; `common.logger.Loggers.CONSUMER_CONSOLE`; обработчик `AppError` мапит `ApiExceptionCode` на HTTP-статусы (PermissionDenied→401, ObjectNotFound→404).

- [ ] **Step 1: Удалить файлы и каталоги**

```bash
git rm -r -q arq_worker core/arq core/sample api/routes/samples common/translations api/middlewares/translations api/configs common/certs api/filebeat.yml api/prometheus.yml api/docker-compose.yml babel.cfg Makefile common/dockerimages/filebeat.Dockerfile
```

- [ ] **Step 2: Переписать common/settings.py**

```python
import os

from dotenv import load_dotenv

DEBUG = True

if DEBUG:
    load_dotenv("envs/test.env")
else:
    load_dotenv("envs/prod.env")

PROJECT_NAME = os.getenv("PROJECT_NAME", "")
PROJECT_PATH = os.path.dirname(os.path.dirname(__file__))

DATABASE_URI = os.getenv("DATABASE_URI", "")

RABBITMQ_URI = os.getenv("RABBITMQ_URI", "")

# AUTH
API_KEY = os.getenv("API_KEY", "")
OPENAPI_TOKEN = os.getenv("OPENAPI_TOKEN", "")

# CONSUMER
WEBHOOK_TIMEOUT = float(os.getenv("WEBHOOK_TIMEOUT", 10))

# OUTBOX RELAY
OUTBOX_POLL_INTERVAL = float(os.getenv("OUTBOX_POLL_INTERVAL", 0.5))
OUTBOX_BATCH_SIZE = int(os.getenv("OUTBOX_BATCH_SIZE", 100))
```

- [ ] **Step 3: Обновить envs/test.env и envs/prod.env**

`envs/test.env`:

```
PROJECT_NAME=PaymentService

DATABASE_URI=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
RABBITMQ_URI=amqp://guest:guest@localhost:5672/

API_KEY=secret-api-key
OPENAPI_TOKEN=some-admin-token
```

`envs/prod.env`:

```
PROJECT_NAME=PaymentService

DATABASE_URI=postgresql+asyncpg://postgres:postgres@postgres:5432/postgres
RABBITMQ_URI=amqp://guest:guest@rabbitmq:5672/

API_KEY=change-me
OPENAPI_TOKEN=change-me
```

- [ ] **Step 4: Переименовать arq-логгеры в common/logger.py**

В `Loggers` заменить `ARQ_CONSOLE = "arq_console"` / `ARQ_FILE = "arq_file"` на:

```python
    CONSUMER_CONSOLE = "consumer_console"
    CONSUMER_FILE = "consumer_file"
```

В `ServiceNames` заменить `ARQ_WORKER = "arq_worker"` на:

```python
    CONSUMER = "consumer"
```

- [ ] **Step 5: Упростить обработчики ошибок (убрать i18n, добавить маппинг статусов)**

`api/core/errors/handlers/app.py` — полное содержимое:

```python
import logging
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from api.core.schemas import ApiResponse
from common.errors import ApiExceptionCode, AppError
from common.logger import Loggers

STATUS_BY_CODE = {
    ApiExceptionCode.InternalServerError: HTTPStatus.INTERNAL_SERVER_ERROR,
    ApiExceptionCode.BadRequest: HTTPStatus.BAD_REQUEST,
    ApiExceptionCode.ValidationError: HTTPStatus.UNPROCESSABLE_ENTITY,
    ApiExceptionCode.PermissionDenied: HTTPStatus.UNAUTHORIZED,
    ApiExceptionCode.ObjectNotFound: HTTPStatus.NOT_FOUND,
}


async def app_exception_handler(request: Request, exc: AppError):
    logger = logging.getLogger(Loggers.API_CONSOLE)
    logger.error(exc)

    api_code = exc.api_code or ApiExceptionCode.InternalServerError
    content = ApiResponse.err(message=exc.message, code=api_code, data=exc.api_data)
    return JSONResponse(status_code=STATUS_BY_CODE[api_code], content=content.md(mode="json"))
```

`api/core/errors/handlers/all.py` — полное содержимое:

```python
import logging
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from api.core.schemas import ApiResponse
from api.utils.traceback_formatter import TracebackFormatter
from common import settings
from common.errors import ApiExceptionCode
from common.logger import Loggers


async def handle_all_exceptions(request: Request, exc: Exception):
    logger = logging.getLogger(Loggers.API_CONSOLE)
    logger.error(exc)

    data = TracebackFormatter.format_traceback_json(exc) if settings.DEBUG else None
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content=ApiResponse.err(
            message="Internal server error",
            code=ApiExceptionCode.InternalServerError,
            data=data,
        ).md(mode="json"),
    )
```

`api/core/errors/handlers/validation.py` — полное содержимое:

```python
from http import HTTPStatus

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.core.schemas import ApiResponse
from common.errors import ApiExceptionCode


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content=ApiResponse.err(
            message="Validation error",
            code=ApiExceptionCode.ValidationError,
            data=exc.errors(),
        ).md(mode="json"),
    )
```

- [ ] **Step 6: Почистить api/core/schemas.py (убрать неиспользуемое)**

Полное содержимое:

```python
from typing import Any

from common.errors import ApiExceptionCode
from common.pydantic.base import BaseModel


class ApiResponseOk[T](BaseModel):
    status: str = "OK"
    code: int = 0
    message: str = ""
    data: T


class ApiResponseErr(BaseModel):
    status: str = "ERR"
    code: ApiExceptionCode
    message: str
    data: Any


class ApiResponse:
    @classmethod
    def ok[T](cls, data: T) -> ApiResponseOk[T]:
        return ApiResponseOk[type(data)](data=data)

    @classmethod
    def err(cls, message: str, code: ApiExceptionCode, data: Any):
        return ApiResponseErr(data=data, message=message, code=code)
```

- [ ] **Step 7: Обновить api/core/enums.py**

```python
from enum import StrEnum


class Tags(StrEnum):
    DOCS = "docs"
    PAYMENTS = "payments"
```

- [ ] **Step 8: Переписать api/asgi.py (без переводов и samples)**

```python
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
```

- [ ] **Step 9: Проверить, что приложение импортируется и линт чистый**

```bash
uv run python -c "from api.asgi import app; print(type(app))"
uv run ruff check .
```

Expected: `<class 'fastapi.applications.FastAPI'>`, ruff без ошибок. Если ruff падает на хвостах удалённого кода — починить в рамках этого шага.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "refactor: strip template extras (arq, i18n, prometheus, filebeat, caddy, samples)"
```

---

### Task 3: Docker-инфраструктура (postgres + rabbitmq) и Makefile

api/consumer добавятся в compose в Task 11 — здесь только инфраструктура, нужная для миграций и тестов.

**Files:**
- Create: `docker-compose.yml` (корень), `Makefile`

**Interfaces:**
- Produces: `make infra` поднимает healthy postgres:5432 и rabbitmq:5672/15672 на localhost; volume `pgdata`; `make test`, `make lint`.

- [ ] **Step 1: Создать корневой docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 3s
      timeout: 3s
      retries: 10

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
```

- [ ] **Step 2: Создать Makefile**

```make
.PHONY: up down logs infra test lint

up:
	docker compose up -d --build

down:
	docker compose down --remove-orphans

logs:
	docker compose logs -f

infra:
	docker compose up -d --wait postgres rabbitmq

test: infra
	uv run pytest

lint:
	uv run ruff check .
```

- [ ] **Step 3: Проверить запуск инфраструктуры**

```bash
make infra && docker compose ps
```

Expected: postgres и rabbitmq в состоянии `healthy`.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml Makefile
git commit -m "feat: add root docker-compose with postgres and rabbitmq"
```

---

### Task 4: Модели payments/outbox и миграция

**Files:**
- Create: `core/payment/__init__.py`, `core/payment/enums.py`, `core/payment/models/__init__.py`, `core/payment/models/payment.py`, `core/outbox/__init__.py`, `core/outbox/enums.py`, `core/outbox/models/__init__.py`, `core/outbox/models/outbox.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/factories.py`, `tests/test_models.py`, `migrations/versions/<hash>_payments_and_outbox.py` (автогенерация)
- Modify: `pyproject.toml` (pytest-конфиг, per-file-ignores)

**Interfaces:**
- Produces: `PaymentModel` (`core.payment.models`) с полями `amount: Decimal`, `currency: Currency`, `description: str | None`, `metadata_` (колонка `metadata`, JSONB), `status: PaymentStatus` (default PENDING), `idempotency_key: str` (unique), `webhook_url: str`, `processed_at: datetime | None` + `id/created_at/updated_at` из BaseModel. `OutboxModel` (`core.outbox.models`) с `event_type: str`, `payload: dict` (JSONB), `status: OutboxStatus` (default PENDING, index), `published_at: datetime | None`. Enums: `Currency.RUB/USD/EUR`, `PaymentStatus.PENDING/SUCCEEDED/FAILED` (значения lowercase), `OutboxStatus.PENDING/PUBLISHED`. Тестовая инфраструктура: фикстуры `create_tables` (session-scoped, create_all/drop_all), `clean_tables` (autouse, TRUNCATE payments/outbox), фабрика `tests.factories.create_pending_payment(**overrides)`.

- [ ] **Step 1: Настроить pytest в pyproject.toml**

Добавить в конец `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
```

В `[tool.ruff.lint.per-file-ignores]` добавить строку:

```toml
"tests/conftest.py" = ["E402"]
```

- [ ] **Step 2: Написать conftest и падающий тест на модели**

`tests/__init__.py` — пустой.

`tests/conftest.py`:

```python
import os

# Env выставляется ДО импорта common.settings: load_dotenv не перекрывает
# уже существующие переменные окружения.
os.environ.setdefault("DATABASE_URI", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
os.environ.setdefault("API_KEY", "test-api-key")

import pytest_asyncio
from sqlalchemy import text

from common.db.connect import engine
from common.models.base import Base
from common.utils import import_all_models

import_all_models()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(create_tables):
    yield
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE payments, outbox"))
```

`tests/factories.py`:

```python
import uuid
from decimal import Decimal

from common.db.connect import Session
from core.payment.models import PaymentModel


async def create_pending_payment(**overrides) -> PaymentModel:
    fields = {
        "amount": Decimal("100.50"),
        "currency": "RUB",
        "idempotency_key": uuid.uuid4().hex,
        "webhook_url": "http://localhost:9000/webhook",
        **overrides,
    }
    async with Session() as session:
        payment = PaymentModel(**fields)
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment
```

`tests/test_models.py`:

```python
import pytest
from sqlalchemy.exc import IntegrityError

from core.payment.enums import PaymentStatus
from tests.factories import create_pending_payment


async def test_payment_defaults():
    payment = await create_pending_payment()
    assert payment.id
    assert payment.status == PaymentStatus.PENDING
    assert payment.processed_at is None


async def test_idempotency_key_is_unique():
    await create_pending_payment(idempotency_key="dup-key")
    with pytest.raises(IntegrityError):
        await create_pending_payment(idempotency_key="dup-key")
```

- [ ] **Step 3: Убедиться, что тесты падают**

```bash
make infra && uv run pytest tests/test_models.py -v
```

Expected: FAIL/ERROR — `ModuleNotFoundError: core.payment`.

- [ ] **Step 4: Создать enums и модели**

`core/payment/__init__.py`, `core/payment/models/__init__.py`, `core/outbox/__init__.py`, `core/outbox/models/__init__.py` — см. ниже; остальные пустые.

`core/payment/enums.py`:

```python
from enum import StrEnum


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class OutboxEventType(StrEnum):
    PAYMENT_CREATED = "payment.created"
```

`core/outbox/enums.py`:

```python
from enum import StrEnum


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
```

`core/payment/models/payment.py`:

```python
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Enum, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import BaseModel
from core.payment.enums import Currency, PaymentStatus


class PaymentModel(BaseModel):
    __tablename__ = "payments"

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    webhook_url: Mapped[str] = mapped_column(String, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

`core/payment/models/__init__.py`:

```python
from core.payment.models.payment import PaymentModel

__all__ = ["PaymentModel"]
```

`core/outbox/models/outbox.py`:

```python
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import BaseModel
from core.outbox.enums import OutboxStatus


class OutboxModel(BaseModel):
    __tablename__ = "outbox"

    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, name="outbox_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=OutboxStatus.PENDING,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

`core/outbox/models/__init__.py`:

```python
from core.outbox.models.outbox import OutboxModel

__all__ = ["OutboxModel"]
```

- [ ] **Step 5: Прогнать тесты**

```bash
uv run pytest tests/test_models.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Сгенерировать и применить миграцию**

БД сбрасывается, чтобы create_all из тестов не помешал autogenerate:

```bash
docker compose down -v && make infra
uv run alembic revision --autogenerate -m "payments and outbox"
uv run alembic upgrade head
```

Открыть сгенерированный файл в `migrations/versions/`, проверить: создаются `payments` (unique index по `idempotency_key`) и `outbox` (index по `status`), enum-типы `currency`, `payment_status`, `outbox_status` со значениями из спеки.

- [ ] **Step 7: Проверить таблицы в БД**

```bash
uv run python -c "
import asyncio
from sqlalchemy import inspect
from common.db.connect import engine

async def main():
    async with engine.connect() as conn:
        print(sorted(await conn.run_sync(lambda c: inspect(c).get_table_names())))

asyncio.run(main())
"
```

Expected: `['alembic_version', 'outbox', 'payments']`.

- [ ] **Step 8: Полный прогон и commit**

```bash
uv run pytest && uv run ruff check .
git add -A
git commit -m "feat: add payments and outbox models with initial migration"
```

---

### Task 5: POST /api/v1/payments (идемпотентность, outbox, X-API-Key)

**Files:**
- Create: `core/payment/dto/__init__.py` (пустой), `core/payment/dto/create_payment.py`, `core/payment/dto/events.py`, `core/payment/cases/__init__.py` (пустой), `core/payment/cases/create_payment.py`, `core/payment/providers.py`, `api/routes/payments/__init__.py` (пустой), `api/routes/payments/router.py`, `api/routes/payments/controller/__init__.py`, `api/routes/payments/controller/payments.py`, `api/routes/payments/schemas/__init__.py` (пустой), `api/routes/payments/schemas/payments_req.py`, `api/routes/payments/schemas/payments_resp.py`, `tests/test_api_payments.py`
- Modify: `api/core/dependencies/auth.py` (добавить X-API-Key), `api/asgi.py` (подключить роутер)

**Interfaces:**
- Consumes: `PaymentModel`, `OutboxModel`, enums из Task 4; `ContainerTypeDI`, `AppError`, `ApiExceptionCode` из шаблона.
- Produces: `CreatePaymentCase(session).execute(dto: CreatePaymentDTO) -> PaymentModel`; `PaymentCreatedEvent(payment_id: str)` (`core.payment.dto.events`); dependency `AuthApiKeyDI`; схемы `CreatePaymentReq`, `PaymentCreatedResp`; роутер `api.routes.payments.router.router` (prefix `/api/v1/payments`).

- [ ] **Step 1: Написать падающие тесты**

`tests/test_api_payments.py`:

```python
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from api.asgi import app
from common.db.connect import Session
from core.outbox.models import OutboxModel
from core.payment.models import PaymentModel

HEADERS = {"X-API-Key": "test-api-key", "Idempotency-Key": "key-1"}
BODY = {
    "amount": "100.50",
    "currency": "RUB",
    "description": "Заказ №1",
    "metadata": {"order_id": 42},
    "webhook_url": "http://localhost:9000/webhook",
}


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def count_rows(model) -> int:
    async with Session() as session:
        return (await session.execute(select(func.count(model.id)))).scalar_one()


async def test_create_payment_returns_202(client):
    resp = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    assert resp.status_code == 202
    data = resp.json()
    assert data["payment_id"]
    assert data["status"] == "pending"
    assert data["created_at"]


async def test_create_payment_writes_payment_and_outbox(client):
    resp = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    payment_id = resp.json()["payment_id"]
    assert await count_rows(PaymentModel) == 1
    async with Session() as session:
        outbox = (await session.execute(select(OutboxModel))).scalar_one()
    assert outbox.event_type == "payment.created"
    assert outbox.payload == {"payment_id": payment_id}
    assert outbox.status == "pending"


async def test_same_idempotency_key_returns_same_payment(client):
    first = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    second = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    assert second.status_code == 202
    assert second.json()["payment_id"] == first.json()["payment_id"]
    assert await count_rows(PaymentModel) == 1
    assert await count_rows(OutboxModel) == 1


async def test_outbox_failure_rolls_back_payment(client, monkeypatch):
    def broken_outbox(**kwargs):
        raise RuntimeError("outbox unavailable")

    monkeypatch.setattr("core.payment.cases.create_payment.OutboxModel", broken_outbox)
    resp = await client.post("/api/v1/payments", json=BODY, headers=HEADERS)
    assert resp.status_code == 500
    assert await count_rows(PaymentModel) == 0


async def test_missing_api_key_returns_401(client):
    resp = await client.post("/api/v1/payments", json=BODY, headers={"Idempotency-Key": "key-1"})
    assert resp.status_code == 401


async def test_wrong_api_key_returns_401(client):
    headers = {"X-API-Key": "wrong", "Idempotency-Key": "key-1"}
    resp = await client.post("/api/v1/payments", json=BODY, headers=headers)
    assert resp.status_code == 401


async def test_missing_idempotency_key_returns_422(client):
    resp = await client.post("/api/v1/payments", json=BODY, headers={"X-API-Key": "test-api-key"})
    assert resp.status_code == 422


async def test_invalid_body_returns_422(client):
    bad = {**BODY, "amount": "-5", "currency": "GBP"}
    resp = await client.post("/api/v1/payments", json=bad, headers=HEADERS)
    assert resp.status_code == 422
```

- [ ] **Step 2: Убедиться, что тесты падают**

```bash
uv run pytest tests/test_api_payments.py -v
```

Expected: все FAIL (404 вместо 202 — роутера ещё нет).

- [ ] **Step 3: DTO и события**

`core/payment/dto/create_payment.py`:

```python
from decimal import Decimal
from typing import Any

from pydantic import Field

from common.pydantic.base import BaseModel
from core.payment.enums import Currency


class CreatePaymentDTO(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: Currency
    description: str | None = None
    metadata: dict[str, Any] | None = None
    webhook_url: str
    idempotency_key: str
```

`core/payment/dto/events.py`:

```python
from common.pydantic.base import BaseModel


class PaymentCreatedEvent(BaseModel):
    payment_id: str
```

- [ ] **Step 4: Use case создания платежа**

`core/payment/cases/create_payment.py`:

```python
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.outbox.models import OutboxModel
from core.payment.dto.create_payment import CreatePaymentDTO
from core.payment.dto.events import PaymentCreatedEvent
from core.payment.enums import OutboxEventType
from core.payment.models import PaymentModel


class CreatePaymentCase:
    """Создаёт платёж и outbox-событие в одной транзакции (Outbox pattern).

    Идемпотентность: платёж с уже известным idempotency_key возвращается
    как есть; гонка параллельных запросов разрешается unique constraint'ом.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, dto: CreatePaymentDTO) -> PaymentModel:
        existing = await self._get_by_idempotency_key(dto.idempotency_key)
        if existing:
            return existing

        payment = PaymentModel(
            amount=dto.amount,
            currency=dto.currency,
            description=dto.description,
            metadata_=dto.metadata,
            idempotency_key=dto.idempotency_key,
            webhook_url=dto.webhook_url,
        )
        self.session.add(payment)
        await self.session.flush()
        self.session.add(
            OutboxModel(
                event_type=OutboxEventType.PAYMENT_CREATED,
                payload=PaymentCreatedEvent(payment_id=payment.id).md(),
            )
        )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self._get_by_idempotency_key(dto.idempotency_key)
            if existing is None:
                raise
            return existing
        await self.session.refresh(payment)
        return payment

    async def _get_by_idempotency_key(self, key: str) -> PaymentModel | None:
        smt = select(PaymentModel).where(PaymentModel.idempotency_key == key)
        return (await self.session.execute(smt)).scalar_one_or_none()
```

`core/payment/providers.py`:

```python
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.payment.cases.create_payment import CreatePaymentCase


class CreatePaymentProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def init(self, session: AsyncSession) -> CreatePaymentCase:
        return CreatePaymentCase(session)


providers = [CreatePaymentProvider()]
```

- [ ] **Step 5: Аутентификация по X-API-Key**

Добавить в конец `api/core/dependencies/auth.py`:

```python
api_key_security = APIKeyHeader(name="X-API-Key", auto_error=False)
ApiKeyDI = Depends(api_key_security)
ApiKeyDIType = Annotated[str | None, ApiKeyDI]


async def auth_api_key_di(api_key: ApiKeyDIType):
    if not api_key or api_key != settings.API_KEY:
        raise AppError(
            message="Invalid or missing API key",
            api_code=ApiExceptionCode.PermissionDenied,
        )
    return api_key


AuthApiKeyDI = Depends(auth_api_key_di)
```

В первой строке импортов файла заменить `from fastapi.security import APIKeyQuery, ...` так, чтобы был и `APIKeyHeader`:

```python
from fastapi.security import APIKeyHeader, APIKeyQuery, HTTPAuthorizationCredentials, HTTPBearer
```

- [ ] **Step 6: Схемы запроса/ответа**

`api/routes/payments/schemas/payments_req.py`:

```python
from decimal import Decimal
from typing import Any

from pydantic import Field, HttpUrl

from common.pydantic.base import BaseModel
from core.payment.enums import Currency


class CreatePaymentReq(BaseModel):
    amount: Decimal = Field(gt=0, description="Сумма платежа")
    currency: Currency = Field(description="Валюта: RUB, USD или EUR")
    description: str | None = Field(default=None, description="Описание платежа")
    metadata: dict[str, Any] | None = Field(default=None, description="Произвольные метаданные")
    webhook_url: HttpUrl = Field(description="URL для уведомления о результате")
```

`api/routes/payments/schemas/payments_resp.py`:

```python
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from common.pydantic.base import BaseModel
from core.payment.enums import Currency, PaymentStatus


class PaymentCreatedResp(BaseModel):
    payment_id: str = Field(validation_alias="id")
    status: PaymentStatus
    created_at: datetime


class PaymentResp(BaseModel):
    payment_id: str = Field(validation_alias="id")
    amount: Decimal
    currency: Currency
    description: str | None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_")
    status: PaymentStatus
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
```

- [ ] **Step 7: Контроллер и роутер**

`api/routes/payments/controller/__init__.py`:

```python
from api.routes.payments.controller.payments import create_payment

__all__ = ["create_payment"]
```

`api/routes/payments/controller/payments.py`:

```python
from api.core.dependencies.container import ContainerTypeDI
from api.routes.payments.schemas.payments_req import CreatePaymentReq
from api.routes.payments.schemas.payments_resp import PaymentCreatedResp
from core.payment.cases.create_payment import CreatePaymentCase
from core.payment.dto.create_payment import CreatePaymentDTO


async def create_payment(container: ContainerTypeDI, model: CreatePaymentReq, idempotency_key: str):
    case = await container.get(CreatePaymentCase)
    dto = CreatePaymentDTO(
        amount=model.amount,
        currency=model.currency,
        description=model.description,
        metadata=model.metadata,
        webhook_url=str(model.webhook_url),
        idempotency_key=idempotency_key,
    )
    payment = await case.execute(dto)
    return PaymentCreatedResp.model_validate(payment)
```

`api/routes/payments/router.py`:

```python
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Header

from api.core.dependencies.auth import AuthApiKeyDI
from api.core.dependencies.container import ContainerTypeDI
from api.core.enums import Tags
from api.routes.payments.schemas.payments_req import CreatePaymentReq
from api.routes.payments.schemas.payments_resp import PaymentCreatedResp

from . import controller

router = APIRouter(prefix="/api/v1/payments", tags=[Tags.PAYMENTS], dependencies=[AuthApiKeyDI])

ROOT = ""


@router.post(ROOT, response_model=PaymentCreatedResp, status_code=HTTPStatus.ACCEPTED)
async def create_payment(
    container: ContainerTypeDI,
    model: CreatePaymentReq,
    idempotency_key: Annotated[str, Header(min_length=1)],
):
    return await controller.create_payment(container, model, idempotency_key)
```

В `api/asgi.py` добавить импорт и подключение:

```python
from api.routes.payments.router import router as payments_router
```

```python
app.include_router(payments_router)
```

- [ ] **Step 8: Прогнать тесты**

```bash
uv run pytest tests/test_api_payments.py -v
```

Expected: 8 passed. (`Header()` сам маппит `idempotency_key` на заголовок `Idempotency-Key`, отсутствие даёт 422 через validation handler.)

- [ ] **Step 9: Полный прогон и commit**

```bash
uv run pytest && uv run ruff check .
git add -A
git commit -m "feat: add POST /api/v1/payments with idempotency, outbox and API key auth"
```

---

### Task 6: GET /api/v1/payments/{payment_id}

**Files:**
- Modify: `api/routes/payments/router.py`, `api/routes/payments/controller/payments.py`, `api/routes/payments/controller/__init__.py`
- Test: `tests/test_api_payments.py` (дополнить)

**Interfaces:**
- Consumes: `PaymentResp` из Task 5, `create_pending_payment` из Task 4.
- Produces: `GET /api/v1/payments/{payment_id}` → 200 `PaymentResp` | 404.

- [ ] **Step 1: Дописать падающие тесты в tests/test_api_payments.py**

```python
async def test_get_payment_returns_details(client):
    from tests.factories import create_pending_payment

    payment = await create_pending_payment(description="Заказ №1", metadata_={"order_id": 42})
    resp = await client.get(f"/api/v1/payments/{payment.id}", headers={"X-API-Key": "test-api-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_id"] == payment.id
    assert data["status"] == "pending"
    assert data["currency"] == "RUB"
    assert data["metadata"] == {"order_id": 42}
    assert data["webhook_url"] == "http://localhost:9000/webhook"
    assert data["processed_at"] is None


async def test_get_unknown_payment_returns_404(client):
    resp = await client.get("/api/v1/payments/no-such-id", headers={"X-API-Key": "test-api-key"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Убедиться, что тесты падают**

```bash
uv run pytest tests/test_api_payments.py -v -k get_
```

Expected: 2 FAIL (404 от FastAPI без нашего конверта / 405).

- [ ] **Step 3: Контроллер и роут**

Добавить в `api/routes/payments/controller/payments.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.payments.schemas.payments_resp import PaymentResp
from common.errors import ApiExceptionCode, AppError
from core.payment.models import PaymentModel


async def get_payment(container: ContainerTypeDI, payment_id: str):
    session = await container.get(AsyncSession)
    smt = select(PaymentModel).where(PaymentModel.id == payment_id)
    payment = (await session.execute(smt)).scalar_one_or_none()
    if not payment:
        raise AppError(
            message="Payment not found",
            api_code=ApiExceptionCode.ObjectNotFound,
            api_data={"payment_id": payment_id},
        )
    return PaymentResp.model_validate(payment)
```

Обновить `api/routes/payments/controller/__init__.py`:

```python
from api.routes.payments.controller.payments import create_payment, get_payment

__all__ = ["create_payment", "get_payment"]
```

Добавить в `api/routes/payments/router.py` (импорт `PaymentResp` — в общий блок импортов схем):

```python
PAYMENT_ID = "/{payment_id}"


@router.get(PAYMENT_ID, response_model=PaymentResp)
async def get_payment(container: ContainerTypeDI, payment_id: str):
    return await controller.get_payment(container, payment_id)
```

- [ ] **Step 4: Прогнать тесты и commit**

```bash
uv run pytest && uv run ruff check .
git add -A
git commit -m "feat: add GET /api/v1/payments/{payment_id}"
```

---

### Task 7: Топология RabbitMQ

**Files:**
- Create: `common/broker.py`, `tests/test_broker_topology.py`

**Interfaces:**
- Produces (используется задачами 8, 10, 11): константы `EXCHANGE_NAME = "payments"`, `QUEUE_NAME = ROUTING_KEY = "payments.new"`, `DLQ_NAME = "payments.new.dlq"`, `MAX_ATTEMPTS = 3`, `RETRY_DELAYS_MS = [2000, 4000, 8000]`; объекты `PAYMENTS_EXCHANGE: RabbitExchange`, `PAYMENTS_QUEUE: RabbitQueue`, `RETRY_QUEUES: list[RabbitQueue]`, `DLQ: RabbitQueue`; функции `retry_queue_name(attempt: int) -> str`, `create_broker() -> RabbitBroker`, `async declare_topology(broker: RabbitBroker) -> None`.

- [ ] **Step 1: Написать падающий тест**

`tests/test_broker_topology.py`:

```python
from common.broker import DLQ, PAYMENTS_EXCHANGE, PAYMENTS_QUEUE, RETRY_QUEUES, retry_queue_name


def test_main_queue_and_exchange():
    assert PAYMENTS_EXCHANGE.name == "payments"
    assert PAYMENTS_QUEUE.name == "payments.new"
    assert PAYMENTS_QUEUE.durable is True


def test_retry_queues_exponential_ttl_and_dlx():
    assert [q.name for q in RETRY_QUEUES] == [
        "payments.new.retry.1",
        "payments.new.retry.2",
        "payments.new.retry.3",
    ]
    assert [q.arguments["x-message-ttl"] for q in RETRY_QUEUES] == [2000, 4000, 8000]
    for queue in RETRY_QUEUES:
        assert queue.arguments["x-dead-letter-exchange"] == "payments"
        assert queue.arguments["x-dead-letter-routing-key"] == "payments.new"


def test_dlq():
    assert DLQ.name == "payments.new.dlq"
    assert retry_queue_name(2) == "payments.new.retry.2"
```

- [ ] **Step 2: Убедиться, что тест падает**

```bash
uv run pytest tests/test_broker_topology.py -v
```

Expected: FAIL — `ModuleNotFoundError: common.broker`.

- [ ] **Step 3: Реализовать common/broker.py**

```python
from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from common import settings

EXCHANGE_NAME = "payments"
QUEUE_NAME = "payments.new"
ROUTING_KEY = QUEUE_NAME
DLQ_NAME = "payments.new.dlq"

MAX_ATTEMPTS = 3
RETRY_DELAYS_MS = [2000, 4000, 8000]

PAYMENTS_EXCHANGE = RabbitExchange(EXCHANGE_NAME, type=ExchangeType.DIRECT, durable=True)
PAYMENTS_QUEUE = RabbitQueue(QUEUE_NAME, durable=True, routing_key=ROUTING_KEY)


def retry_queue_name(attempt: int) -> str:
    return f"{QUEUE_NAME}.retry.{attempt}"


# Retry-очереди без консюмера: сообщение лежит в них TTL миллисекунд,
# затем через dead-letter-exchange возвращается в основную очередь.
RETRY_QUEUES = [
    RabbitQueue(
        retry_queue_name(attempt),
        durable=True,
        arguments={
            "x-message-ttl": ttl_ms,
            "x-dead-letter-exchange": EXCHANGE_NAME,
            "x-dead-letter-routing-key": ROUTING_KEY,
        },
    )
    for attempt, ttl_ms in enumerate(RETRY_DELAYS_MS, start=1)
]

DLQ = RabbitQueue(DLQ_NAME, durable=True)


def create_broker() -> RabbitBroker:
    return RabbitBroker(settings.RABBITMQ_URI)


async def declare_topology(broker: RabbitBroker) -> None:
    """Идемпотентно объявляет всю топологию; вызывается и relay, и консюмером.

    Binding основной очереди объявляется явно, чтобы публикации relay
    не терялись, если консюмер ещё не стартовал. Retry-очереди и DLQ
    получают сообщения через default exchange (по имени очереди), binding
    им не нужен.
    """
    exchange = await broker.declare_exchange(PAYMENTS_EXCHANGE)
    main_queue = await broker.declare_queue(PAYMENTS_QUEUE)
    await main_queue.bind(exchange, routing_key=ROUTING_KEY)
    for queue in [*RETRY_QUEUES, DLQ]:
        await broker.declare_queue(queue)
```

- [ ] **Step 4: Прогнать тесты и commit**

```bash
uv run pytest && uv run ruff check .
git add common/broker.py tests/test_broker_topology.py
git commit -m "feat: add RabbitMQ topology with retry queues and DLQ"
```

---

### Task 8: Outbox relay

**Files:**
- Create: `core/outbox/relay.py`, `tests/test_outbox_relay.py`
- Modify: `api/asgi.py` (lifespan), `tests/factories.py` (фабрика outbox)

**Interfaces:**
- Consumes: `OutboxModel`, `OutboxStatus` (Task 4), `create_broker`/`declare_topology`/`PAYMENTS_EXCHANGE`/`ROUTING_KEY` (Task 7).
- Produces: `async relay_pending_once(publish: Callable[[OutboxModel], Awaitable[None]], batch_size: int) -> int`; `async run_relay_loop(publish) -> None` (бесконечный цикл, ошибки логирует и продолжает).

- [ ] **Step 1: Дописать фабрику в tests/factories.py**

```python
from core.outbox.models import OutboxModel


async def create_outbox_event(payment_id: str = "p-1") -> OutboxModel:
    async with Session() as session:
        event = OutboxModel(event_type="payment.created", payload={"payment_id": payment_id})
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event
```

- [ ] **Step 2: Написать падающие тесты**

`tests/test_outbox_relay.py`:

```python
import pytest
from sqlalchemy import select

from common.db.connect import Session
from core.outbox.enums import OutboxStatus
from core.outbox.models import OutboxModel
from core.outbox.relay import relay_pending_once
from tests.factories import create_outbox_event


async def get_all_events() -> list[OutboxModel]:
    async with Session() as session:
        return list((await session.execute(select(OutboxModel))).scalars())


async def test_relay_publishes_pending_and_marks_published():
    await create_outbox_event("p-1")
    await create_outbox_event("p-2")
    published = []

    async def publish(event: OutboxModel) -> None:
        published.append(event.payload["payment_id"])

    count = await relay_pending_once(publish, batch_size=10)

    assert count == 2
    assert sorted(published) == ["p-1", "p-2"]
    events = await get_all_events()
    assert all(e.status == OutboxStatus.PUBLISHED for e in events)
    assert all(e.published_at is not None for e in events)


async def test_relay_skips_already_published():
    await create_outbox_event("p-1")

    async def publish(event: OutboxModel) -> None:
        pass

    assert await relay_pending_once(publish, batch_size=10) == 1
    assert await relay_pending_once(publish, batch_size=10) == 0


async def test_relay_keeps_pending_on_publish_error():
    await create_outbox_event("p-1")

    async def publish(event: OutboxModel) -> None:
        raise RuntimeError("broker down")

    with pytest.raises(RuntimeError):
        await relay_pending_once(publish, batch_size=10)

    events = await get_all_events()
    assert events[0].status == OutboxStatus.PENDING
```

- [ ] **Step 3: Убедиться, что тесты падают**

```bash
uv run pytest tests/test_outbox_relay.py -v
```

Expected: FAIL — `ModuleNotFoundError: core.outbox.relay`.

- [ ] **Step 4: Реализовать core/outbox/relay.py**

```python
import asyncio
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy import select

from common import settings
from common.db.connect import Session
from common.logger import Loggers
from common.utils import now_utc
from core.outbox.enums import OutboxStatus
from core.outbox.models import OutboxModel

PublishFn = Callable[[OutboxModel], Awaitable[None]]

logger = logging.getLogger(Loggers.API_CONSOLE)


async def relay_pending_once(publish: PublishFn, batch_size: int) -> int:
    """Один проход relay: публикует pending-события и помечает их published.

    FOR UPDATE SKIP LOCKED позволяет запускать несколько экземпляров api
    без двойной обработки строк. Гарантия — at-least-once: при падении
    посреди пачки транзакция откатывается и уже опубликованные события
    уйдут повторно; дубли гасит идемпотентность консюмера.
    """
    async with Session() as session:
        smt = (
            select(OutboxModel)
            .where(OutboxModel.status == OutboxStatus.PENDING)
            .order_by(OutboxModel.created_at)
            .with_for_update(skip_locked=True)
            .limit(batch_size)
        )
        events = (await session.execute(smt)).scalars().all()
        for event in events:
            await publish(event)
            event.status = OutboxStatus.PUBLISHED
            event.published_at = now_utc()
        await session.commit()
        return len(events)


async def run_relay_loop(publish: PublishFn) -> None:
    while True:
        try:
            await relay_pending_once(publish, settings.OUTBOX_BATCH_SIZE)
        except Exception:
            logger.exception("Outbox relay iteration failed")
        await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)
```

- [ ] **Step 5: Прогнать тесты**

```bash
uv run pytest tests/test_outbox_relay.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Подключить relay в lifespan api/asgi.py**

Полное новое содержимое `api/asgi.py`:

```python
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
from common.broker import PAYMENTS_EXCHANGE, ROUTING_KEY, create_broker, declare_topology
from common.errors import AppError
from core.outbox.models import OutboxModel
from core.outbox.relay import run_relay_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker = create_broker()
    await broker.connect()
    await declare_topology(broker)

    async def publish_event(event: OutboxModel) -> None:
        await broker.publish(
            event.payload,
            exchange=PAYMENTS_EXCHANGE,
            routing_key=ROUTING_KEY,
            persist=True,
        )

    relay_task = asyncio.create_task(run_relay_loop(publish_event))
    yield
    relay_task.cancel()
    with suppress(asyncio.CancelledError):
        await relay_task
    await broker.stop()


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
```

Примечание: httpx ASGITransport lifespan не запускает, поэтому API-тесты не требуют RabbitMQ. Если установленный FastStream — 0.5.x, вместо `broker.stop()` использовать `broker.close()`.

- [ ] **Step 7: Полный прогон и commit**

```bash
uv run pytest && uv run ruff check .
git add -A
git commit -m "feat: add outbox relay with background publish loop in api lifespan"
```

---

### Task 9: Обработка платежа (эмуляция шлюза, webhook, ProcessPaymentCase)

**Files:**
- Create: `core/payment/errors.py`, `core/payment/services/__init__.py` (пустой), `core/payment/services/base.py`, `core/payment/services/gateway.py`, `core/payment/services/webhook.py`, `core/payment/cases/process_payment.py`, `tests/test_process_payment.py`

**Interfaces:**
- Consumes: `PaymentModel`, `PaymentStatus` (Task 4), `create_pending_payment` (Task 4).
- Produces (используется Task 10): `ProcessPaymentCase(session, gateway: PaymentGateway, webhook: WebhookDelivery).execute(payment_id: str) -> PaymentModel`; протоколы `PaymentGateway` (`async process(payment) -> PaymentStatus`), `WebhookDelivery` (`async send(payment) -> None`); классы `PaymentGatewayEmulator(success_rate=0.9, min_delay=2.0, max_delay=5.0)`, `WebhookSender(timeout: float | None = None)`; исключения `PaymentProcessingError`, `WebhookDeliveryError(PaymentProcessingError)` в `core.payment.errors`.

- [ ] **Step 1: Написать падающие тесты**

`tests/test_process_payment.py`:

```python
import pytest

from common.db.connect import Session
from core.payment.cases.process_payment import ProcessPaymentCase
from core.payment.enums import PaymentStatus
from core.payment.errors import PaymentProcessingError, WebhookDeliveryError
from core.payment.models import PaymentModel
from tests.factories import create_pending_payment


class RecordingGateway:
    def __init__(self, result: PaymentStatus):
        self.result = result
        self.calls = 0

    async def process(self, payment: PaymentModel) -> PaymentStatus:
        self.calls += 1
        return self.result


class RecordingWebhook:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[str] = []

    async def send(self, payment: PaymentModel) -> None:
        if self.fail:
            raise WebhookDeliveryError("webhook unavailable")
        self.sent.append(payment.id)


async def run_case(payment_id: str, gateway, webhook) -> PaymentModel:
    async with Session() as session:
        case = ProcessPaymentCase(session, gateway, webhook)
        return await case.execute(payment_id)


async def get_payment(payment_id: str) -> PaymentModel:
    async with Session() as session:
        return await session.get_one(PaymentModel, payment_id)


async def test_success_updates_status_and_sends_webhook():
    payment = await create_pending_payment()
    gateway = RecordingGateway(PaymentStatus.SUCCEEDED)
    webhook = RecordingWebhook()

    await run_case(payment.id, gateway, webhook)

    stored = await get_payment(payment.id)
    assert stored.status == PaymentStatus.SUCCEEDED
    assert stored.processed_at is not None
    assert webhook.sent == [payment.id]


async def test_gateway_failure_is_business_result_not_error():
    payment = await create_pending_payment()
    gateway = RecordingGateway(PaymentStatus.FAILED)
    webhook = RecordingWebhook()

    await run_case(payment.id, gateway, webhook)

    stored = await get_payment(payment.id)
    assert stored.status == PaymentStatus.FAILED
    assert webhook.sent == [payment.id]


async def test_redelivery_skips_gateway_but_resends_webhook():
    payment = await create_pending_payment()
    gateway = RecordingGateway(PaymentStatus.SUCCEEDED)
    webhook = RecordingWebhook()

    await run_case(payment.id, gateway, webhook)
    await run_case(payment.id, gateway, webhook)

    assert gateway.calls == 1
    assert webhook.sent == [payment.id, payment.id]


async def test_webhook_failure_raises_but_status_is_committed():
    payment = await create_pending_payment()
    gateway = RecordingGateway(PaymentStatus.SUCCEEDED)
    webhook = RecordingWebhook(fail=True)

    with pytest.raises(WebhookDeliveryError):
        await run_case(payment.id, gateway, webhook)

    stored = await get_payment(payment.id)
    assert stored.status == PaymentStatus.SUCCEEDED


async def test_unknown_payment_raises_processing_error():
    with pytest.raises(PaymentProcessingError):
        await run_case("no-such-id", RecordingGateway(PaymentStatus.SUCCEEDED), RecordingWebhook())
```

- [ ] **Step 2: Убедиться, что тесты падают**

```bash
uv run pytest tests/test_process_payment.py -v
```

Expected: FAIL — `ModuleNotFoundError: core.payment.cases.process_payment`.

- [ ] **Step 3: Ошибки и протоколы**

`core/payment/errors.py`:

```python
class PaymentProcessingError(Exception):
    """Ошибка обработки платежа: сообщение уходит в retry, затем в DLQ."""


class WebhookDeliveryError(PaymentProcessingError):
    """Webhook не доставлен (сетевая ошибка, таймаут или не-2xx ответ)."""
```

`core/payment/services/base.py`:

```python
from typing import Protocol

from core.payment.enums import PaymentStatus
from core.payment.models import PaymentModel


class PaymentGateway(Protocol):
    async def process(self, payment: PaymentModel) -> PaymentStatus: ...


class WebhookDelivery(Protocol):
    async def send(self, payment: PaymentModel) -> None: ...
```

- [ ] **Step 4: Эмулятор шлюза и отправитель webhook**

`core/payment/services/gateway.py`:

```python
import asyncio
import random

from core.payment.enums import PaymentStatus
from core.payment.models import PaymentModel


class PaymentGatewayEmulator:
    """Эмуляция внешнего платёжного шлюза: 2-5 сек обработки, 90% успех."""

    def __init__(self, success_rate: float = 0.9, min_delay: float = 2.0, max_delay: float = 5.0):
        self.success_rate = success_rate
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def process(self, payment: PaymentModel) -> PaymentStatus:
        await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))
        if random.random() < self.success_rate:
            return PaymentStatus.SUCCEEDED
        return PaymentStatus.FAILED
```

`core/payment/services/webhook.py`:

```python
import httpx

from common import settings
from core.payment.errors import WebhookDeliveryError
from core.payment.models import PaymentModel


class WebhookSender:
    def __init__(self, timeout: float | None = None):
        self.timeout = timeout if timeout is not None else settings.WEBHOOK_TIMEOUT

    async def send(self, payment: PaymentModel) -> None:
        body = {
            "payment_id": payment.id,
            "status": payment.status,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "metadata": payment.metadata_,
            "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(payment.webhook_url, json=body)
        except httpx.HTTPError as exc:
            raise WebhookDeliveryError(f"Webhook request failed: {exc}") from exc
        if response.status_code // 100 != 2:
            raise WebhookDeliveryError(f"Webhook returned {response.status_code}")
```

- [ ] **Step 5: ProcessPaymentCase**

`core/payment/cases/process_payment.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession

from common.utils import now_utc
from core.payment.enums import PaymentStatus
from core.payment.errors import PaymentProcessingError
from core.payment.models import PaymentModel
from core.payment.services.base import PaymentGateway, WebhookDelivery


class ProcessPaymentCase:
    """Обрабатывает платёж: эмуляция шлюза -> статус в БД -> webhook.

    Идемпотентен к повторной доставке: платёж с финальным статусом
    не обрабатывается шлюзом повторно, но webhook отправляется снова —
    ретраи существуют именно для недоставленных webhook'ов. Статус
    коммитится ДО отправки webhook, чтобы retry не менял результат платежа.
    """

    def __init__(self, session: AsyncSession, gateway: PaymentGateway, webhook: WebhookDelivery):
        self.session = session
        self.gateway = gateway
        self.webhook = webhook

    async def execute(self, payment_id: str) -> PaymentModel:
        payment = await self.session.get(PaymentModel, payment_id)
        if payment is None:
            raise PaymentProcessingError(f"Payment {payment_id} not found")

        if payment.status == PaymentStatus.PENDING:
            payment.status = await self.gateway.process(payment)
            payment.processed_at = now_utc()
            await self.session.commit()

        await self.webhook.send(payment)
        return payment
```

- [ ] **Step 6: Прогнать тесты и commit**

```bash
uv run pytest && uv run ruff check .
git add -A
git commit -m "feat: add payment processing case with gateway emulator and webhook sender"
```

---

### Task 10: Consumer и retry-маршрутизация

**Files:**
- Create: `consumer/__init__.py` (пустой), `consumer/retry.py`, `consumer/app.py`, `tests/test_retry_routing.py`

**Interfaces:**
- Consumes: всё из задач 7 и 9.
- Produces: `async route_failure(broker, payload: dict, attempt: int) -> None` (`consumer.retry`); FastStream-приложение `consumer.app:app` (запуск: `faststream run consumer.app:app`).

- [ ] **Step 1: Написать падающие тесты**

`tests/test_retry_routing.py`:

```python
from unittest.mock import AsyncMock

from consumer.retry import route_failure


async def test_first_failure_goes_to_retry_1():
    broker = AsyncMock()
    await route_failure(broker, {"payment_id": "p-1"}, attempt=0)
    broker.publish.assert_awaited_once_with(
        {"payment_id": "p-1"},
        queue="payments.new.retry.1",
        headers={"x-attempt": 1},
        persist=True,
    )


async def test_second_failure_goes_to_retry_2():
    broker = AsyncMock()
    await route_failure(broker, {"payment_id": "p-1"}, attempt=1)
    broker.publish.assert_awaited_once_with(
        {"payment_id": "p-1"},
        queue="payments.new.retry.2",
        headers={"x-attempt": 2},
        persist=True,
    )


async def test_exhausted_attempts_go_to_dlq():
    broker = AsyncMock()
    await route_failure(broker, {"payment_id": "p-1"}, attempt=3)
    broker.publish.assert_awaited_once_with(
        {"payment_id": "p-1"},
        queue="payments.new.dlq",
        headers={"x-attempt": 3},
        persist=True,
    )
```

- [ ] **Step 2: Убедиться, что тесты падают**

```bash
uv run pytest tests/test_retry_routing.py -v
```

Expected: FAIL — `ModuleNotFoundError: consumer.retry`.

- [ ] **Step 3: Реализовать consumer/retry.py**

```python
from faststream.rabbit import RabbitBroker

from common.broker import DLQ_NAME, MAX_ATTEMPTS, retry_queue_name


async def route_failure(broker: RabbitBroker, payload: dict, attempt: int) -> None:
    """Маршрутизирует упавшее сообщение: retry с экспоненциальной задержкой или DLQ.

    attempt — число уже сделанных ретраев (из заголовка x-attempt, 0 при
    первой доставке). Публикация идёт через default exchange по имени
    очереди; из retry-очереди сообщение вернётся в payments.new через DLX.
    """
    if attempt >= MAX_ATTEMPTS:
        await broker.publish(
            payload,
            queue=DLQ_NAME,
            headers={"x-attempt": attempt},
            persist=True,
        )
        return

    next_attempt = attempt + 1
    await broker.publish(
        payload,
        queue=retry_queue_name(next_attempt),
        headers={"x-attempt": next_attempt},
        persist=True,
    )
```

- [ ] **Step 4: Прогнать тесты retry**

```bash
uv run pytest tests/test_retry_routing.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Реализовать consumer/app.py**

```python
import logging

from faststream import FastStream
from faststream.rabbit.annotations import RabbitMessage

from common.broker import PAYMENTS_EXCHANGE, PAYMENTS_QUEUE, create_broker, declare_topology
from common.db.connect import Session
from common.logger import Loggers, setup_console_logger
from consumer.retry import route_failure
from core.payment.cases.process_payment import ProcessPaymentCase
from core.payment.dto.events import PaymentCreatedEvent
from core.payment.services.gateway import PaymentGatewayEmulator
from core.payment.services.webhook import WebhookSender

setup_console_logger(Loggers.CONSUMER_CONSOLE)
logger = logging.getLogger(Loggers.CONSUMER_CONSOLE)

broker = create_broker()
app = FastStream(broker)


@app.after_startup
async def setup_topology() -> None:
    await declare_topology(broker)


@broker.subscriber(PAYMENTS_QUEUE, PAYMENTS_EXCHANGE)
async def handle_payment_created(event: PaymentCreatedEvent, message: RabbitMessage) -> None:
    """Единственный обработчик: эмуляция шлюза, статус в БД, webhook.

    Любая ошибка обработки уходит в route_failure (retry/DLQ), после чего
    сообщение подтверждается. Если сломается сама публикация в retry,
    исключение выйдет из обработчика и брокер вернёт сообщение заново.
    """
    attempt = int(message.headers.get("x-attempt", 0))
    try:
        async with Session() as session:
            case = ProcessPaymentCase(session, PaymentGatewayEmulator(), WebhookSender())
            payment = await case.execute(event.payment_id)
        logger.info(f"Payment {event.payment_id} processed: {payment.status}")
    except Exception:
        logger.exception(f"Processing failed for payment {event.payment_id} (attempt {attempt})")
        await route_failure(broker, event.md(), attempt)
```

- [ ] **Step 6: Smoke-проверка запуска консюмера**

```bash
make infra
timeout 15 uv run faststream run consumer.app:app; test $? -eq 124 && echo "CONSUMER OK"
```

Expected: консюмер стартует, объявляет топологию, живёт до истечения timeout → `CONSUMER OK`. В management UI (http://localhost:15672, guest/guest) видны очереди `payments.new`, `payments.new.retry.1..3`, `payments.new.dlq`.

- [ ] **Step 7: Полный прогон и commit**

```bash
uv run pytest && uv run ruff check .
git add -A
git commit -m "feat: add FastStream consumer with retry routing and DLQ"
```

---

### Task 11: Полный docker-compose и e2e smoke

**Files:**
- Modify: `docker-compose.yml` (добавить api, consumer)
- Create: `scripts/__init__.py` (пустой), `scripts/webhook_receiver.py`

**Interfaces:**
- Consumes: всё построенное ранее; `common/dockerimages/python.Dockerfile` (существующий).
- Produces: `docker compose up -d --build` поднимает рабочую систему из 4 сервисов; api на localhost:8000.

- [ ] **Step 1: Добавить сервисы api и consumer в docker-compose.yml**

Дополнить `services:` (postgres и rabbitmq не трогать):

```yaml
  api:
    build:
      context: .
      dockerfile: common/dockerimages/python.Dockerfile
    command: sh -c "alembic upgrade head && uvicorn api.asgi:app --host 0.0.0.0 --port 8000"
    environment: &app_env
      DATABASE_URI: postgresql+asyncpg://postgres:postgres@postgres:5432/postgres
      RABBITMQ_URI: amqp://guest:guest@rabbitmq:5672/
      API_KEY: ${API_KEY:-secret-api-key}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy

  consumer:
    build:
      context: .
      dockerfile: common/dockerimages/python.Dockerfile
    command: faststream run consumer.app:app
    environment: *app_env
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
```

- [ ] **Step 2: Создать scripts/webhook_receiver.py (демо-приёмник для README и smoke)**

```python
from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    print("Webhook received:", await request.json(), flush=True)
    return {"ok": True}
```

- [ ] **Step 3: Поднять систему**

```bash
docker compose up -d --build && docker compose ps
```

Expected: 4 сервиса, postgres/rabbitmq healthy, api и consumer запущены (логи без трейсбеков: `docker compose logs api consumer | tail -50`).

- [ ] **Step 4: E2E happy path**

```bash
uv run uvicorn scripts.webhook_receiver:app --port 9000 --host 0.0.0.0 > /tmp/claude-0/-root-projects-Sergey-other-PaymentService/f0c256bb-197a-404d-b26f-4f2bd45a004f/scratchpad/receiver.log 2>&1 &
sleep 2
curl -s -X POST http://localhost:8000/api/v1/payments \
  -H 'X-API-Key: secret-api-key' -H 'Idempotency-Key: e2e-1' -H 'Content-Type: application/json' \
  -d '{"amount": "100.50", "currency": "RUB", "description": "e2e", "metadata": {"order_id": 1}, "webhook_url": "http://host.docker.internal:9000/webhook"}'
```

Expected: 202 с `payment_id`, `status: pending`. Далее (подставить payment_id):

```bash
sleep 8
curl -s http://localhost:8000/api/v1/payments/<payment_id> -H 'X-API-Key: secret-api-key'
grep "Webhook received" /tmp/claude-0/-root-projects-Sergey-other-PaymentService/f0c256bb-197a-404d-b26f-4f2bd45a004f/scratchpad/receiver.log
```

Expected: статус `succeeded` (или `failed` — 10% случаев), `processed_at` заполнен; в логе приёмника строка webhook с тем же payment_id и статусом.

- [ ] **Step 5: E2E retry → DLQ**

```bash
curl -s -X POST http://localhost:8000/api/v1/payments \
  -H 'X-API-Key: secret-api-key' -H 'Idempotency-Key: e2e-dlq-1' -H 'Content-Type: application/json' \
  -d '{"amount": "10", "currency": "USD", "webhook_url": "http://host.docker.internal:9/unreachable"}'
sleep 45
docker compose exec rabbitmq rabbitmqctl list_queues name messages
```

Expected: после ~4 попыток (обработка 2-5с + задержки 2/4/8с) в `payments.new.dlq` 1 сообщение; статус платежа в БД при этом финальный (шлюз отработал, недоставлен только webhook). Остановить приёмник: `kill %1` (или по pid).

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml scripts/
git commit -m "feat: add api and consumer services to docker-compose"
```

---

### Task 12: README

**Files:**
- Modify: `README.md` (полная переработка)

**Interfaces:**
- Consumes: фактические команды из Makefile/compose, реальные примеры из Task 11.

- [ ] **Step 1: Переписать README.md**

Структура (все команды и примеры — реально проверенные в Task 11, скопировать оттуда):

1. **Название и описание** — асинхронный сервис процессинга платежей: API → Outbox → RabbitMQ → Consumer → Webhook.
2. **Архитектура** — текстовая схема потока; кратко: Outbox pattern (таблица + relay-поллер в процессе api, at-least-once), идемпотентность (unique `Idempotency-Key`, повторная доставка не переэмулирует платёж), retry (очереди TTL 2с/4с/8с + DLX, заголовок `x-attempt`), DLQ `payments.new.dlq` после 3 ретраев.
3. **Стек** — FastAPI, Pydantic v2, SQLAlchemy 2.0 async, PostgreSQL, RabbitMQ + FastStream, Alembic, Docker Compose.
4. **Запуск** — `docker compose up -d --build` (или `make up`); что поднимается (4 сервиса); api: http://localhost:8000, RabbitMQ UI: http://localhost:15672 (guest/guest); docs: http://localhost:8000/docs/?token=some-admin-token.
5. **Переменные окружения** — таблица: `API_KEY`, `DATABASE_URI`, `RABBITMQ_URI`, `WEBHOOK_TIMEOUT`, `OUTBOX_POLL_INTERVAL`, `OUTBOX_BATCH_SIZE`, `PROJECT_NAME`, `OPENAPI_TOKEN`; где задаются (envs/*.env, compose).
6. **Примеры API** — curl POST (все заголовки, тело, ответ 202) и повторный POST с тем же Idempotency-Key (тот же payment_id); curl GET (ответ 200 полный JSON); ошибки 401/404/422 — формат конверта.
7. **Webhook** — формат тела уведомления (`payment_id`, `status`, `amount` строкой, `currency`, `metadata`, `processed_at`); запуск демо-приёмника `uv run uvicorn scripts.webhook_receiver:app --port 9000`; из контейнера consumer хост доступен как `host.docker.internal`.
8. **Как посмотреть DLQ** — сценарий с недоступным webhook_url из Task 11 Step 5, `rabbitmqctl list_queues` и management UI.
9. **Разработка** — `uv sync`, `make infra`, `make test` (тесты используют локальный postgres из compose), `make lint`, миграции (`uv run alembic ...`).

- [ ] **Step 2: Проверить команды из README**

Каждую команду README прогнать или сверить с уже прогнанными в Task 11; расхождений быть не должно.

- [ ] **Step 3: Финальный прогон всего**

```bash
uv run pytest && uv run ruff check .
docker compose up -d --build && docker compose ps
```

Expected: тесты зелёные, линт чистый, 4 сервиса работают.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for payment service"
```
