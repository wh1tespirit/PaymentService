# PaymentService

Асинхронный сервис процессинга платежей. API принимает платёж и сразу отвечает `202 Accepted`, реальная обработка идёт в фоне: событие уходит через Outbox в RabbitMQ, консюмер эмулирует платёжный шлюз и уведомляет клиента webhook'ом. Недоставленные webhook'и ретраятся с экспоненциальной задержкой, безнадёжные — оседают в DLQ.

## Архитектура

```
POST /api/v1/payments
        │
        ▼
   ┌──────────────────────────────┐
   │ payments + outbox (одна TX)  │  ← Outbox pattern: платёж и событие
   └──────────────────────────────┘     коммитятся атомарно
        │
        │ outbox relay (фоновая задача в процессе api, поллинг 0.5с)
        ▼
   exchange payments ──routing key payments.new──► очередь payments.new
        │
        ▼
   consumer (FastStream)
        │  эмуляция шлюза (2-5с, 90% успех) → статус в БД → webhook
        │
        └── ошибка ──► payments.new.retry.1 (TTL 2с) ─┐
                       payments.new.retry.2 (TTL 4с) ─┼─ DLX ─► payments.new
                       payments.new.retry.3 (TTL 8с) ─┘
                              │
                       после 3 ретраев ──► payments.new.dlq
```

**Outbox pattern.** Платёж и событие `payment.created` пишутся в одной транзакции, поэтому «платёж создан, а событие потеряно» невозможно. Relay-поллер в процессе `api` выбирает `pending`-события (`FOR UPDATE SKIP LOCKED` — можно запускать несколько реплик api), публикует их и помечает `published`. Гарантия доставки — **at-least-once**: при падении посреди пачки события уйдут повторно.

**Идемпотентность** — на двух уровнях:
- *На входе*: `Idempotency-Key` лежит в колонке с unique-индексом. Повторный POST с тем же ключом и тем же телом возвращает тот же `payment_id` и не создаёт ни второго платежа, ни второго outbox-события; тот же ключ с другим телом — `409 Conflict`, чтобы новый платёж не потерялся молча. Гонка параллельных запросов разрешается самим constraint'ом: вставка целиком обёрнута в обработку `IntegrityError`.
- *При повторной доставке*: строка платежа берётся под `SELECT ... FOR UPDATE`, поэтому параллельные доставки одного события выстраиваются в очередь и шлюз отрабатывает ровно один раз. Webhook при этом шлётся снова — ретраи существуют именно ради недоставленных уведомлений.

**Retry.** Без плагинов RabbitMQ: три очереди с `x-message-ttl` 2000/4000/8000 мс и без консюмера. Сообщение отлёживает TTL и через `x-dead-letter-exchange` возвращается в `payments.new`. Номер попытки едет в заголовке `x-attempt` (0 при первой доставке). При `x-attempt >= 3` сообщение уходит в `payments.new.dlq`. Итого: первичная доставка + 3 ретрая.

**Ничего не теряется молча.** У `payments.new` тоже есть `x-dead-letter-exchange` на DLQ: ack-политика FastStream по умолчанию — reject без requeue, поэтому сообщение с нечитаемым телом или падение самой публикации в retry-очередь иначе уничтожили бы событие. С DLX оно остаётся видимым в `payments.new.dlq`.

**Статус коммитится до отправки webhook** — чтобы ретраи не переписывали результат платежа.

## Стек

FastAPI · Pydantic v2 · SQLAlchemy 2.0 (async) · PostgreSQL · RabbitMQ + FastStream · Alembic · dishka · uv · Docker Compose

## Запуск

```bash
docker compose up -d --build   # или make up
```

Поднимается 4 сервиса: `postgres`, `rabbitmq`, `api`, `consumer`. Миграции применяются автоматически при старте `api`.

| Что | Где |
|---|---|
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs/?token=some-admin-token |
| Scalar | http://localhost:8000/docs/scalar?token=some-admin-token |
| RabbitMQ UI | http://localhost:15672 (guest/guest) |

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `API_KEY` | `secret-api-key` | Ключ для заголовка `X-API-Key` |
| `DATABASE_URI` | `postgresql+asyncpg://postgres:postgres@postgres:5432/postgres` | Подключение к PostgreSQL |
| `RABBITMQ_URI` | `amqp://guest:guest@rabbitmq:5672/` | Подключение к RabbitMQ |
| `DEBUG` | `false` | Отдавать traceback в теле ответа 500 (только для локальной отладки) |
| `WEBHOOK_TIMEOUT` | `10` | Таймаут HTTP-запроса webhook, сек |
| `GATEWAY_SUCCESS_RATE` | `0.9` | Доля успешных ответов эмулятора шлюза |
| `GATEWAY_MIN_DELAY` / `GATEWAY_MAX_DELAY` | `2` / `5` | Границы задержки эмулятора, сек |
| `OUTBOX_POLL_INTERVAL` | `0.5` | Пауза между проходами relay, сек |
| `OUTBOX_BATCH_SIZE` | `100` | Размер пачки событий за проход |
| `PROJECT_NAME` | `PaymentService` | Имя проекта в логах и OpenAPI |
| `OPENAPI_TOKEN` | `some-admin-token` | Токен доступа к `/docs` |
| `ENV_FILE` | `envs/test.env` | Файл с дефолтами для локального запуска |

Локальная разработка берёт значения из `envs/test.env`, контейнеры — из блока `environment` в `docker-compose.yml` (сам файл в образ не копируется). Переменные окружения имеют приоритет над `.env`-файлами.

## API

### Создание платежа

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H 'X-API-Key: secret-api-key' \
  -H 'Idempotency-Key: order-1' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": "100.50",
    "currency": "RUB",
    "description": "Заказ №1",
    "metadata": {"order_id": 1},
    "webhook_url": "http://host.docker.internal:9000/webhook"
  }'
```

`202 Accepted`:

```json
{
  "payment_id": "92bed8e885b3468288058132a5d559b5",
  "status": "pending",
  "created_at": "2026-08-19T15:09:56.747055Z"
}
```

Повторный запрос с тем же `Idempotency-Key` и тем же телом вернёт **тот же** `payment_id` и не создаст второй платёж. Тот же ключ с другим телом — `409 Conflict`.

Валюты: `RUB`, `USD`, `EUR`. `amount` — строка или число больше нуля, не больше двух знаков после запятой и 12 значащих цифр (ограничение колонки `Numeric(12, 2)`).

### Получение платежа

```bash
curl http://localhost:8000/api/v1/payments/92bed8e885b3468288058132a5d559b5 \
  -H 'X-API-Key: secret-api-key'
```

`200 OK`:

```json
{
  "payment_id": "92bed8e885b3468288058132a5d559b5",
  "amount": "100.50",
  "currency": "RUB",
  "description": "e2e",
  "metadata": {"order_id": 1},
  "status": "succeeded",
  "webhook_url": "http://webhook-receiver:9000/webhook",
  "created_at": "2026-08-19T15:09:56.747055Z",
  "processed_at": "2026-08-19T15:10:00.650347Z"
}
```

Статусы: `pending` → `succeeded` | `failed`.

### Ошибки

Успешные ответы плоские, ошибки — в конверте `{"status": "ERR", "code": ..., "message": ..., "data": ...}`.

```jsonc
// 401 — нет или неверный X-API-Key
{"status": "ERR", "code": 4, "message": "Invalid or missing API key", "data": null}

// 404 — платёж не найден
{"status": "ERR", "code": 5, "message": "Payment not found", "data": {"payment_id": "no-such-id"}}

// 409 — Idempotency-Key уже использован с другим телом запроса
{"status": "ERR", "code": 6, "message": "Idempotency-Key already used with a different payload",
 "data": {"payment_id": "92bed8e885b3468288058132a5d559b5"}}

// 422 — ошибка валидации (тело или отсутствующий Idempotency-Key)
{"status": "ERR", "code": 3, "message": "Validation error",
 "data": [{"type": "missing", "loc": ["header", "idempotency-key"], "msg": "Field required", "input": null}]}
```

## Webhook

После обработки консюмер шлёт `POST` на `webhook_url`:

```json
{
  "payment_id": "92bed8e885b3468288058132a5d559b5",
  "status": "succeeded",
  "amount": "100.50",
  "currency": "RUB",
  "metadata": {"order_id": 1},
  "processed_at": "2026-08-19T15:10:00.650347+00:00"
}
```

Доставка считается успешной при ответе 2xx. Таймаут, сетевая ошибка или не-2xx — повод для ретрая.

Демо-приёмник для проверки:

```bash
uv run uvicorn scripts.webhook_receiver:app --port 9000 --host 0.0.0.0
```

Из контейнера `consumer` хост доступен как `host.docker.internal` (проброшен через `extra_hosts`), поэтому `webhook_url` будет `http://host.docker.internal:9000/webhook`.

> Если на хосте включён фаервол (ufw, firewalld) с `INPUT DROP`, обращения из контейнера к хосту будут отваливаться по таймауту. Тогда либо разрешите доступ с docker-подсети, либо поднимите приёмник контейнером в той же сети:
> ```bash
> docker run -d --name webhook-receiver --network paymentservice_default paymentservice-api \
>   uvicorn scripts.webhook_receiver:app --host 0.0.0.0 --port 9000
> ```
> и укажите `"webhook_url": "http://webhook-receiver:9000/webhook"`.

## Как посмотреть DLQ

Создайте платёж с заведомо недоступным `webhook_url`:

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H 'X-API-Key: secret-api-key' \
  -H 'Idempotency-Key: dlq-demo-1' \
  -H 'Content-Type: application/json' \
  -d '{"amount": "10", "currency": "USD", "webhook_url": "http://host.docker.internal:9/unreachable"}'
```

Через ~60 секунд (обработка 2-5с + задержки 2/4/8с + таймауты webhook) сообщение окажется в DLQ:

```bash
docker compose exec rabbitmq rabbitmqctl list_queues name messages
```

```
payments.new            0
payments.new.retry.1    0
payments.new.retry.2    0
payments.new.retry.3    0
payments.new.dlq        1
```

В логах консюмера видны все четыре попытки:

```bash
docker compose logs consumer | grep "Processing failed"
# ... (attempt 0) ... (attempt 1) ... (attempt 2) ... (attempt 3)
```

Сам платёж при этом имеет финальный статус — шлюз отработал один раз, недоставлен только webhook. Очереди также видны в management UI: http://localhost:15672 → Queues.

## Разработка

```bash
uv sync          # окружение (Python 3.12, см. .python-version)
make infra       # только postgres + rabbitmq
make test        # uv run pytest (поднимет инфраструктуру сам)
make lint        # uv run ruff check .
```

Тесты работают с реальным PostgreSQL из compose, но в отдельной базе `payments_test`: она создаётся на время сессии и дропается после, поэтому прогон не трогает данные работающего стека. Имя базы обязано оканчиваться на `_test` — иначе conftest откажется стартовать.

Миграции:

```bash
uv run alembic revision --autogenerate -m "описание"
uv run alembic upgrade head
uv run alembic downgrade -1
```

### Структура

```
api/          FastAPI: роуты → контроллеры, middleware, обработчики ошибок
consumer/     FastStream-приложение: обработчик payments.new и retry-маршрутизация
core/         бизнес-логика: payment (модели, DTO, use cases, сервисы), outbox (модели, relay)
common/       общее: settings, БД, брокер, логгер, DI-контейнер, базовые модели
migrations/   Alembic
scripts/      демо-приёмник webhook
tests/        pytest
```
