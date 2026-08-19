from typing import Protocol

from core.payment.enums import PaymentStatus
from core.payment.models import PaymentModel


class PaymentGateway(Protocol):
    async def process(self, payment: PaymentModel) -> PaymentStatus: ...


class WebhookDelivery(Protocol):
    async def send(self, payment: PaymentModel) -> None: ...
