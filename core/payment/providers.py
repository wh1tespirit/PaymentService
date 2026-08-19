from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.payment.cases.create_payment import CreatePaymentCase


class CreatePaymentProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def init(self, session: AsyncSession) -> CreatePaymentCase:
        return CreatePaymentCase(session)


providers = [CreatePaymentProvider()]
