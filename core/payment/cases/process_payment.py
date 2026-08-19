from sqlalchemy.ext.asyncio import AsyncSession

from common.utils import now_utc
from core.payment.enums import PaymentStatus
from core.payment.errors import PaymentProcessingError
from core.payment.models import PaymentModel
from core.payment.services.base import PaymentGateway, WebhookDelivery


class ProcessPaymentCase:
    """Обрабатывает платёж: эмуляция шлюза -> статус в БД -> webhook.

    Идемпотентен к повторной доставке: платёж с финальным статусом
    не обрабатывается шлюзом повторно, но webhook отправляется снова —
    ретраи существуют именно для недоставленных webhook'ов. Статус
    коммитится ДО отправки webhook, чтобы retry не менял результат платежа.
    """

    def __init__(self, session: AsyncSession, gateway: PaymentGateway, webhook: WebhookDelivery):
        self.session = session
        self.gateway = gateway
        self.webhook = webhook

    async def execute(self, payment_id: str) -> PaymentModel:
        payment = await self.session.get(PaymentModel, payment_id)
        if payment is None:
            raise PaymentProcessingError(f"Payment {payment_id} not found")

        if payment.status == PaymentStatus.PENDING:
            payment.status = await self.gateway.process(payment)
            payment.processed_at = now_utc()
            await self.session.commit()

        await self.webhook.send(payment)
        return payment
