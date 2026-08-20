import os

# Env выставляется ДО импорта common.settings: load_dotenv не перекрывает
# уже существующие переменные окружения.
os.environ.setdefault("DATABASE_URI", "postgresql+asyncpg://postgres:postgres@localhost:5432/payments_test")
os.environ.setdefault("API_KEY", "test-api-key")

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from common import settings
from common.db.connect import engine
from common.models.base import Base
from common.utils import import_all_models

import_all_models()

TEST_DB_URL = make_url(settings.DATABASE_URI)

# Тесты дропают схему целиком, поэтому имя базы обязано быть тестовым:
# иначе прогон снесёт данные и миграции работающего стека.
if not TEST_DB_URL.database or not TEST_DB_URL.database.endswith("_test"):
    raise RuntimeError(
        f"Тесты запускаются только на базе с суффиксом _test, получено: {TEST_DB_URL.database!r}. "
        "Задайте DATABASE_URI на отдельную базу."
    )


async def _ensure_test_database() -> None:
    """Создаёт тестовую базу, если её ещё нет (CREATE DATABASE не работает в транзакции)."""
    admin_engine = create_async_engine(TEST_DB_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_URL.database}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB_URL.database}"'))
    finally:
        await admin_engine.dispose()


async def _drop_test_database() -> None:
    admin_engine = create_async_engine(TEST_DB_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_URL.database}" WITH (FORCE)'))
    finally:
        await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    await _ensure_test_database()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    await _drop_test_database()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(create_tables):
    yield
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE payments, outbox"))
