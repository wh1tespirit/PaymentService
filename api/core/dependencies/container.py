from collections.abc import AsyncGenerator
from typing import Annotated

from dishka import AsyncContainer
from fastapi import Depends

from common.container import Container


async def container_di() -> AsyncGenerator[AsyncContainer, None]:
    async with Container() as context:
        yield context


ContainerDI = Depends(container_di)
ContainerTypeDI = Annotated[AsyncContainer, ContainerDI]
