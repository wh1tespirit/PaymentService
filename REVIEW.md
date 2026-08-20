# Ревью реализации по ТЗ

Дата: 2026-08-19. Ревью — сверка кода с ТЗ (`redirect.pdf`) плюс многоагентный поиск багов с верификацией каждого утверждения по исходникам и воспроизведением на живом compose-стеке.

**Статус: все находки исправлены.** 37 тестов проходят, `ruff check` чист, docker-стек проверен end-to-end.

## Вердикт по ТЗ

ТЗ выполнено полностью — все пункты «Требований к результату» реализованы и покрыты тестами. Архитектура аккуратная: Outbox с `FOR UPDATE SKIP LOCKED`, retry через TTL-очереди + DLX без плагинов, идемпотентность на unique-констрейнте, подробный README.

| Требование | Статус |
|---|---|
| Сущность Payment (все 9 полей) | ✅ `core/payment/models/payment.py` |
| POST /api/v1/payments: Idempotency-Key, 202, payment_id/status/created_at | ✅ |
| GET /api/v1/payments/{id}: детальная информация | ✅ |
| Событие в `payments.new` при создании | ✅ exchange `payments` → очередь `payments.new` |
| Один consumer: эмуляция 2–5с / 90%, статус в БД, webhook, ретраи | ✅ `consumer/app.py` |
| Outbox pattern | ✅ одна транзакция + relay-поллер |
| Idempotency key | ✅ unique-индекс |
| DLQ после 3 попыток | ✅ `payments.new.dlq` |
| Retry: 3 попытки с экспоненциальной задержкой | ✅ TTL 2с/4с/8с |
| X-API-Key на всех эндпоинтах | ✅ dependency на роутере |
| Стек: FastAPI, Pydantic v2, SQLAlchemy 2 async, PG, RabbitMQ (FastStream), Alembic, Docker | ✅ |
| Модели и миграции payments + outbox | ✅ |
| Compose: postgres, rabbitmq, api, consumer | ✅ |
| README с запуском и примерами | ✅ |

## Найдено и исправлено: баги

### 1. Гонка по Idempotency-Key давала 500 вместо 202

`core/payment/cases/create_payment.py`

INSERT уходил в БД на `flush()`, а `try/except IntegrityError` был обёрнут только вокруг `commit()`. При двух конкурентных POST с одним ключом проигравший получал 500, хотя docstring и README обещали идемпотентный ответ.

**Исправлено:** вся вставка (включая `flush`) внутри `try/except IntegrityError`. Заодно убран лишний `session.refresh()` после commit (`expire_on_commit=False`, все дефолты клиентские — это был пустой SELECT на каждый POST).
**Тест:** `test_concurrent_requests_with_same_key_create_one_payment` — до фикса падал с `UniqueViolationError`.

### 2. Ошибка вне `try` обработчика молча теряла событие

`consumer/app.py`, `common/broker.py`

Дефолтная ack-политика FastStream 0.7 — `REJECT_ON_ERROR`, то есть reject **без** requeue (проверено по установленному пакету), а у `payments.new` не было DLX. Любое исключение, вышедшее из обработчика, уничтожало сообщение: платёж навсегда `pending`, в DLQ пусто. Под это попадали нечитаемое тело сообщения (декодирование идёт до обработчика), кривой заголовок `x-attempt` (парсился до `try`) и падение самой публикации в retry-очередь.

**Исправлено:** у `payments.new` появился `x-dead-letter-exchange` на DLQ, парсинг заголовка вынесен в устойчивый `read_attempt()`, docstring приведён в соответствие с реальным поведением.
**Проверено вживую:** нечитаемое сообщение, отправленное в `payments.new`, дошло до DLQ с `x-death.reason=rejected` — раньше оно исчезало бесследно.

### 3. `make test` уничтожал данные и схему работающего стека

`tests/conftest.py`

Тесты ходили в ту же БД `postgres`, что и compose-стек, делали `TRUNCATE` после каждого теста и `drop_all` + `DROP TABLE alembic_version` в конце сессии. Стек был обнаружен ровно в этом состоянии (api отдавал 500 `UndefinedTableError`).

**Исправлено:** тесты работают в отдельной базе `payments_test` — она создаётся на время сессии и дропается после. Имя базы обязано оканчиваться на `_test`, иначе conftest падает с явным сообщением: это защита от повторения той же ошибки.
**Проверено вживую:** после полного прогона тестов живой стек отвечает 200.

### 4. Конкурентная повторная доставка обрабатывала платёж дважды

`core/payment/cases/process_payment.py`

`session.get` без блокировки: две одновременные доставки одного `payment_id` обе видели `pending`, обе вызывали шлюз (для реального шлюза — двойное списание) и могли записать разные финальные статусы.

**Исправлено:** строка берётся под `with_for_update=True`, транзакция закрывается до отправки webhook — блокировка не держится на время HTTP-запроса.
**Тест:** `test_concurrent_deliveries_call_gateway_once` — до фикса шлюз вызывался дважды.

## Найдено и исправлено: остальное

| # | Что было | Что стало |
|---|---|---|
| 5 | `amount` без ограничений точности: `10.005` молча округлялся, `99999999999` падал с 500 | `max_digits=12, decimal_places=2` под колонку `Numeric(12,2)` → 422 (проверено вживую) |
| 6 | `DEBUG = True` захардкожен: полный traceback с SQL уходил клиенту в каждом 500; `envs/prod.env` — недостижимый мёртвый конфиг; `envs/test.env` с токеном запекался в образ | `DEBUG` из env (по умолчанию `false`), `prod.env` удалён, `envs/` исключены из образа, compose задаёт `PROJECT_NAME`/`OPENAPI_TOKEN` явно |
| 7 | `MAX_ATTEMPTS` и `RETRY_DELAYS_MS` — независимые константы | `MAX_ATTEMPTS = len(RETRY_DELAYS_MS)` |
| 8 | Relay публиковал всё с единственным routing key, игнорируя `event_type` | `core/outbox/publisher.py`: маршрутизация по типу события, незнакомый тип — явная ошибка вместо тихой публикации в чужую очередь |
| 9 | Нет restart policy: упавший контейнер оставался лежать | `restart: unless-stopped` у `api` и `consumer` |
| 10 | Тот же Idempotency-Key с другим телом молча возвращал старый платёж | Сравнение тела запроса → `409 Conflict` (проверено вживую) |
| 11 | Consumer собирал зависимости руками, минуя dishka-контейнер | `ProcessPaymentProvider` + резолв через `Container`, как в API. Штатная dishka-интеграция с FastStream не подошла: она сломана на 0.7 (`No module named 'faststream.broker'`) |
| 12 | `STATUS_BY_CODE[api_code]` без fallback ронял сам обработчик ошибок | `.get(...)` с дефолтом 500 |

Мелочи: общий `httpx.AsyncClient` на процесс вместо нового пула на каждый webhook; relay не спит после полной пачки; частичный индекс `ix_outbox_pending` вместо индекса по всем статусам (+ миграция `b1c7f0a94d12`); `x-attempt` вынесен константой; общий базовый `PaymentPayload` вместо дублирования полей и правил валидации в схеме и DTO; `session.get` вместо `select` по PK; параметры эмулятора шлюза выведены в env; удалён мёртвый код (`ApiResponseOk`/`ApiResponse.ok`, `Loggers.CONSUMER_FILE`, `ServiceNames.CONSUMER`, сломанный `run.py`), `EXPOSE 22` → `EXPOSE 8000`.

## Что проверял и сознательно не менял

- **Корректно и без изменений:** топология брокера (binding основной очереди, TTL/DLX retry-очередей), соответствие миграции моделям, dishka-провайдеры и request-scope, alias'ы в response-схемах, конверт ошибок валидации.
- **CORS** — ТЗ не предполагает браузерного клиента.
- `cache=False` у session-провайдера — осознанное решение, задокументировано комментарием.
- Планы и спеки в `docs/superpowers/` — исторические записи сессии разработки, упоминания удалённых файлов там оставлены как есть.

## Проверка

```
pytest        37 passed
ruff check    All checks passed!
docker        стек пересобран, миграции применились, e2e-цикл пройден
```

E2E на живом стеке: создание 202 → повтор с тем же телом отдаёт тот же `payment_id` → повтор с другим телом 409 → суммы вне `Numeric(12,2)` дают 422 → платёж обработан, webhook доставлен → недоступный webhook исчерпал 3 ретрая (`attempt 0/1/2/3`) и ушёл в DLQ → нечитаемое сообщение тоже попало в DLQ, а не пропало.

> Аргументы очереди `payments.new` изменились (добавлен DLX), поэтому на уже существующей очереди объявление упало бы с `PRECONDITION_FAILED`. У rabbitmq в compose нет volume — достаточно `docker compose down && docker compose up -d --build`, что и было сделано.
