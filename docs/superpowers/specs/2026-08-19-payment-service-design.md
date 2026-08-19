# Спецификация: асинхронный сервис процессинга платежей

Дата: 2026-08-19
Статус: утверждена
Источник требований: `redirect.pdf` (тестовое задание), выполняется строго по ТЗ.

## 1. Цель

Микросервис асинхронной обработки платежей: принимает запросы на оплату,
обрабатывает их через эмуляцию внешнего платёжного шлюза и уведомляет клиента
о результате через webhook. Гарантии доставки — Outbox pattern, идемпотентность,
retry с экспоненциальной задержкой, Dead Letter Queue.

Стек (зафиксирован ТЗ): FastAPI + Pydantic v2, SQLAlchemy 2.0 (async),
PostgreSQL, RabbitMQ (FastStream), Alembic, Docker + docker-compose.

## 2. База проекта и чистка шаблона

Проект строится на существующем шаблоне (форк RLT-LLC/fastapi_template, ветка pgv)
с сохранением его слоистой структуры и паттернов: роут → контроллер → use case
(`core/<домен>/cases`), DI через dishka, модели от `common.models.base.BaseModel`.

Из шаблона удаляется всё, чего нет в ТЗ:

- `arq_worker/`, `core/arq/` и Redis-настройки (заменяются FastStream-консюмером);
- `core/sample/`, `api/routes/samples/` (демо-код);
- Babel/i18n: `common/translations/`, `api/middlewares/translations/`,
  `babel.cfg`, компиляция переводов в compose; обработчики ошибок упрощаются
  до статических англоязычных сообщений;
- Prometheus (`prometheus-client`, `api/prometheus.yml`, `PROMETHEUS_MULTIPROC_DIR`);
- filebeat (`api/filebeat.yml`, `arq_worker/filebeat.yml`, докер-образ filebeat,
  `common/certs/`);
- caddy;
- оба compose-файла (`api/docker-compose.yml`, `arq_worker/docker-compose.yml`) —
  заменяются одним корневым `docker-compose.yml`.

Остаются: dishka DI, логгер, обработчики ошибок (упрощённые), `common/db`,
Alembic, защищённый токеном `/docs`.

Зависимости: добавить `faststream[rabbit]`, `httpx`; dev-группа `pytest`,
`pytest-asyncio`; удалить `arq`, `babel`, `prometheus-client`.

## 3. Архитектура

Один корневой `docker-compose.yml`, строго 4 сервиса по ТЗ:

| Сервис | Содержимое |
|---|---|
| `postgres` | PostgreSQL, healthcheck, named volume |
| `rabbitmq` | `rabbitmq:3-management`, healthcheck, порт management UI наружу |
| `api` | `alembic upgrade head` при старте, затем uvicorn; внутри процесса — фоновая asyncio-задача outbox-relay (стартует/останавливается в lifespan) |
| `consumer` | отдельное FastStream-приложение, пакет `consumer/` |

Outbox-relay живёт в процессе api сознательно: ТЗ фиксирует состав compose из
четырёх сервисов, отдельный пятый контейнер не заводим.

## 4. Модель данных

Обе модели наследуют `BaseModel` шаблона (id — UUID-строка PK, `created_at`,
`updated_at`).

### Таблица `payments`

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | String (UUID) | PK, из BaseModel |
| `amount` | Numeric(12, 2) | not null, > 0 (валидация на уровне Pydantic) |
| `currency` | enum `RUB` / `USD` / `EUR` | not null |
| `description` | String | nullable |
| `metadata` | JSONB (атрибут модели `metadata_`, имя колонки `metadata`) | nullable |
| `status` | enum `pending` / `succeeded` / `failed` | not null, default `pending` |
| `idempotency_key` | String | **unique**, not null, индекс |
| `webhook_url` | String | not null |
| `processed_at` | DateTime(tz) | nullable, заполняется консюмером |

### Таблица `outbox`

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | String (UUID) | PK |
| `event_type` | String | not null, `payment.created` |
| `payload` | JSONB | not null, минимум `{"payment_id": ...}` |
| `status` | enum `pending` / `published` | not null, default `pending`, индекс |
| `published_at` | DateTime(tz) | nullable |

Каталог `migrations/versions` пуст — цепочка начинается с одной
автосгенерированной миграции Alembic, создающей обе таблицы (модель sample
удаляется до генерации).

## 5. API

Все эндпоинты — под статическим API-ключом: заголовок `X-API-Key` сверяется
с `API_KEY` из env через FastAPI-dependency на роутере `/api/v1`;
отсутствие или несовпадение → 401.

### POST `/api/v1/payments`

- Заголовки: `X-API-Key`, `Idempotency-Key` (обязательный; отсутствие → 422).
- Body: `amount` (decimal, > 0), `currency` (RUB/USD/EUR), `description`
  (опционально), `metadata` (объект, опционально), `webhook_url` (обязательный,
  валидный http/https URL).
- Логика (use case `core/payment/cases/create_payment.py`): в **одной
  транзакции** вставляются платёж со статусом `pending` и outbox-запись
  `payment.created`. Дубль по `Idempotency-Key` перехватывается уникальным
  constraint'ом (`IntegrityError` → повторный select) — гонки безопасны;
  возвращается уже существующий платёж, второй платёж и второе событие
  не создаются.
- Ответ: `202 Accepted`, тело `{"payment_id": ..., "status": ..., "created_at": ...}` —
  одинаковое для нового и для повторного запроса.

### GET `/api/v1/payments/{payment_id}`

- Ответ 200: полная информация — `payment_id`, `amount`, `currency`,
  `description`, `metadata`, `status`, `webhook_url`, `created_at`, `processed_at`.
- Неизвестный id → 404.

## 6. Outbox relay

Фоновая asyncio-задача в процессе api, цикл с периодом ~0.5 сек:

1. `SELECT ... FROM outbox WHERE status = 'pending' ORDER BY created_at
   FOR UPDATE SKIP LOCKED LIMIT <batch>`;
2. публикация каждого события в RabbitMQ (persistent delivery mode,
  exchange `payments`, routing key `payments.new`) через FastStream-брокер;
3. `status = 'published'`, `published_at = now()`, commit.

Ошибка публикации → rollback, запись остаётся `pending`, повтор в следующем
цикле. Гарантия — at-least-once; дубли доставки гасятся идемпотентностью
консюмера (п. 7, шаг 2).

## 7. Consumer

Один обработчик очереди `payments.new` (`consumer/`), делающий всё:

1. Получает сообщение `{"payment_id": ...}`.
2. Загружает платёж. Если статус уже не `pending` — эмуляция **пропускается**
   (идемпотентность при повторной доставке), переход к шагу 4. Платёж
   не найден → ошибка обработки (retry: relay мог опередить видимость записи).
3. Эмуляция шлюза: `asyncio.sleep(random.uniform(2, 5))`; с вероятностью 90% —
   `succeeded`, 10% — `failed`. Это **бизнес-результат, не ошибка обработки**:
   в обоих случаях статус и `processed_at` записываются в БД (commit).
4. Отправляет webhook: httpx POST на `webhook_url` с таймаутом, тело
   `{"payment_id", "status", "amount", "currency", "metadata", "processed_at"}`.
   Успех — HTTP 2xx.
5. Любая ошибка обработки (недоступна БД, таймаут/не-2xx webhook) → сообщение
   уходит в retry-механизм (п. 8). При повторной доставке шаг 3 не повторится —
   статус уже финальный, повторится только webhook.

## 8. Retry и DLQ

Классическая схема TTL + dead-letter-exchange, без плагинов:

- Очереди `payments.new.retry.1` / `.2` / `.3` с `x-message-ttl` **2000 / 4000 /
  8000 мс** (экспоненциальная задержка) и DLX, возвращающим сообщение
  в `payments.new`.
- Счётчик попыток — заголовок `x-attempt`. При ошибке обработки консюмер
  публикует копию сообщения в `payments.new.retry.{n+1}` (инкрементировав
  заголовок) и ack'ает оригинал.
- После 3-й неудачной попытки сообщение публикуется в **`payments.new.dlq`** —
  обычную очередь без консюмера; сообщения доступны для инспекции
  в management UI.

Топология (exchange, основная очередь, retry-очереди, DLQ) декларируется при
старте consumer'а и relay (идемпотентные declare).

## 9. Конфигурация (env)

`common/settings.py`; значения по умолчанию — в `envs/test.env`, боевые —
`envs/prod.env`:

- существующие: `PROJECT_NAME`, `DATABASE_URI`, `OPENAPI_TOKEN`;
- новые: `API_KEY` (статический ключ API), `RABBITMQ_URI`
  (`amqp://guest:guest@rabbitmq:5672/`), `WEBHOOK_TIMEOUT` (сек, default 10),
  `OUTBOX_POLL_INTERVAL` (сек, default 0.5), `OUTBOX_BATCH_SIZE` (default 100);
- удаляются: `REDIS_*`, `PROMETHEUS_MULTIPROC_DIR`, `DEFAULT_LOCALE`.

## 10. Тесты

pytest + pytest-asyncio, каталог `tests/`. БД — PostgreSQL (поднимается
compose'ом), брокер в юнит-тестах замокан.

1. **Идемпотентность POST**: два запроса с одним `Idempotency-Key` → 202 оба,
   один и тот же `payment_id`, в БД один платёж и одна outbox-запись.
2. **Атомарность**: успешный POST создаёт платёж и outbox-запись в одной
   транзакции; сбой вставки outbox не оставляет платёж.
3. **Аутентификация**: запрос без/с неверным `X-API-Key` → 401; без
   `Idempotency-Key` → 422.
4. **Консюмер**: (a) успех эмуляции (random замокан) → статус `succeeded`,
   webhook отправлен; (b) неуспех → `failed`, webhook отправлен; (c) redelivery
   с финальным статусом → эмуляция пропущена, webhook отправлен повторно.
5. **Retry/DLQ**: ошибка webhook → публикация в `payments.new.retry.1`
   с `x-attempt: 1`; `x-attempt: 3` и ошибка → публикация в `payments.new.dlq`
   (публикации проверяются на замоканном брокере).

## 11. Документация (README)

README переписывается под сервис: краткое описание архитектуры (схема потока:
API → outbox → relay → RabbitMQ → consumer → webhook; retry-топология),
запуск `docker compose up --build`, таблица переменных окружения, примеры curl
для POST/GET (с заголовками), пример простого webhook-приёмника для проверки,
как посмотреть DLQ в management UI, запуск тестов.

## 12. Вне объёма

- Реальный платёжный шлюз, подпись webhook'ов, HMAC — нет в ТЗ.
- Отдельный сервис-relay, Kafka, transactional outbox через CDC — нет в ТЗ.
- Метрики, трейсинг, i18n — удаляются вместе с обвязкой шаблона.
