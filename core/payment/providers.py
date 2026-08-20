from collections.abc import AsyncGenerator

import httpx
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio.session import AsyncSession

from common import settings
from core.payment.cases.create_payment import CreatePaymentCase
from core.payment.cases.process_payment import ProcessPaymentCase
from core.payment.services.base import PaymentGateway, WebhookDelivery
from core.payment.services.gateway import PaymentGatewayEmulator
from core.payment.services.webhook import WebhookSender


class CreatePaymentProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def init(self, session: AsyncSession) -> CreatePaymentCase:
        return CreatePaymentCase(session)


class PaymentServicesProvider(Provider):
    @provide(scope=Scope.APP)
    def gateway(self) -> PaymentGateway:
        return PaymentGatewayEmulator(
            success_rate=settings.GATEWAY_SUCCESS_RATE,
            min_delay=settings.GATEWAY_MIN_DELAY,
            max_delay=settings.GATEWAY_MAX_DELAY,
        )

    @provide(scope=Scope.APP)
    async def webhook(self) -> AsyncGenerator[WebhookDelivery, None]:
        # Один HTTP-клиент на процесс: keep-alive вместо нового пула соединений
        # на каждую доставку. Закрывается при закрытии контейнера.
        async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT) as client:
            yield WebhookSender(client)


class ProcessPaymentProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def init(
        self,
        session: AsyncSession,
        gateway: PaymentGateway,
        webhook: WebhookDelivery,
    ) -> ProcessPaymentCase:
        return ProcessPaymentCase(session, gateway, webhook)


providers = [CreatePaymentProvider(), PaymentServicesProvider(), ProcessPaymentProvider()]
