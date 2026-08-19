# PaymentService

Сервис платежей на FastAPI. Создан из шаблона
[RLT-LLC/fastapi_template](https://github.com/RLT-LLC/fastapi_template) (ветка `pgv`).

## Стек

- Python 3.12+, FastAPI, Uvicorn
- PostgreSQL + SQLAlchemy 2.0 (async, asyncpg), Alembic
- Redis + arq (фоновые задачи)
- dishka (DI), Babel (i18n), Prometheus (метрики)
- uv для зависимостей, ruff для линта

## Структура

```
api/          HTTP-слой: роуты, middlewares, обработчики ошибок, ASGI-приложение
arq_worker/   воркер фоновых задач: контроллеры, таски, воркеры
core/         бизнес-логика: use cases, DTO, модели домена, сессии
common/       общее: настройки, логгер, db, переводы, docker-образы
migrations/   миграции Alembic
envs/         переменные окружения (test.env / prod.env)
```

## Переменные окружения

`common/settings.py` грузит `envs/test.env` при `DEBUG = True` и `envs/prod.env` иначе.

| Переменная | Назначение |
|---|---|
| `PROJECT_NAME` | имя сервиса: заголовок OpenAPI и поле в логах |
| `DATABASE_URI` | строка подключения PostgreSQL (`postgresql+asyncpg://...`) |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` | подключение к Redis для arq |
| `OPENAPI_TOKEN` | токен доступа к `/docs` и `/openapi.json` |
| `PROMETHEUS_MULTIPROC_DIR` | каталог метрик Prometheus в multiprocess-режиме |

## Запуск

Локально:

```bash
uv sync
uv run python run.py          # http://0.0.0.0:3000, autoreload
```

В Docker (api + arq воркер):

```bash
make up          # поднять оба сервиса
make logs        # логи обоих
make down        # остановить
```

Отдельно: `make up-api` / `make up-arq`, `make logs-api` / `make logs-arq`.

## Миграции

```bash
uv run alembic revision --autogenerate -m "описание"
uv run alembic upgrade head
```

## Обновления из шаблона

Апстрим подключён как remote `template`:

```bash
git fetch template
git merge template/pgv
```
