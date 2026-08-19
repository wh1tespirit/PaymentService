import asyncio
import random

from core.payment.enums import PaymentStatus
from core.payment.models import PaymentModel


class PaymentGatewayEmulator:
    """Эмуляция внешнего платёжного шлюза: 2-5 сек обработки, 90% успех."""

    def __init__(self, success_rate: float = 0.9, min_delay: float = 2.0, max_delay: float = 5.0):
        self.success_rate = success_rate
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def process(self, payment: PaymentModel) -> PaymentStatus:
        await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))
        if random.random() < self.success_rate:
            return PaymentStatus.SUCCEEDED
        return PaymentStatus.FAILED
