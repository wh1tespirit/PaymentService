import uuid
from decimal import Decimal

from common.db.connect import Session
from core.payment.models import PaymentModel


async def create_pending_payment(**overrides) -> PaymentModel:
    fields = {
        "amount": Decimal("100.50"),
        "currency": "RUB",
        "idempotency_key": uuid.uuid4().hex,
        "webhook_url": "http://localhost:9000/webhook",
        **overrides,
    }
    async with Session() as session:
        payment = PaymentModel(**fields)
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment
