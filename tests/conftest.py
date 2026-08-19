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
