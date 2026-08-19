import uuid
from decimal import Decimal

from common.db.connect import Session
from core.outbox.models import OutboxModel
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


async def create_outbox_event(payment_id: str = "p-1") -> OutboxModel:
    async with Session() as session:
        event = OutboxModel(event_type="payment.created", payload={"payment_id": payment_id})
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event
