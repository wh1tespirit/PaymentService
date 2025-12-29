from collections.abc import AsyncGenerator
from typing import Any

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio.session import AsyncSession

from common.db.connect import Session


class SessionProvider(Provider):
    @provide(scope=Scope.REQUEST, cache=False) # Отключаем кеширование сессии, чтобы каждое получение = новая сессия
    async def init(self) -> AsyncGenerator[AsyncSession, Any]:
        async with Session() as session:
            yield session


providers = [SessionProvider()]
