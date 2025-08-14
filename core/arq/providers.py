from collections.abc import AsyncGenerator
from typing import Any

from dishka import Provider, Scope, provide

from common import settings
from core.arq.service import ArqService


class ArqProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def init(self) -> AsyncGenerator[ArqService, Any]:
        arq = ArqService(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
        )
        await arq.connect()
        yield arq
        await arq.disconnect()


providers = [ArqProvider()]
