from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.sample.cases.create_sample import CreateSampleCase


class CreateSampleProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def init(self, session: AsyncSession) -> CreateSampleCase:
        return CreateSampleCase(session)


providers = [CreateSampleProvider()]
