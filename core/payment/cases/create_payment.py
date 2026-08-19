from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.outbox.models import OutboxModel
from core.payment.dto.create_payment import CreatePaymentDTO
from core.payment.dto.events import PaymentCreatedEvent
from core.payment.enums import OutboxEventType
from core.payment.models import PaymentModel


class CreatePaymentCase:
    """Создаёт платёж и outbox-событие в одной транзакции (Outbox pattern).

    Идемпотентность: платёж с уже известным idempotency_key возвращается
    как есть; гонка параллельных запросов разрешается unique constraint'ом.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, dto: CreatePaymentDTO) -> PaymentModel:
        existing = await self._get_by_idempotency_key(dto.idempotency_key)
        if existing:
            return existing

        payment = PaymentModel(
            amount=dto.amount,
            currency=dto.currency,
            description=dto.description,
            metadata_=dto.metadata,
            idempotency_key=dto.idempotency_key,
            webhook_url=dto.webhook_url,
        )
        self.session.add(payment)
        await self.session.flush()
        self.session.add(
            OutboxModel(
                event_type=OutboxEventType.PAYMENT_CREATED,
                payload=PaymentCreatedEvent(payment_id=payment.id).md(),
            )
        )
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self._get_by_idempotency_key(dto.idempotency_key)
            if existing is None:
                raise
            return existing
        await self.session.refresh(payment)
        return payment

    async def _get_by_idempotency_key(self, key: str) -> PaymentModel | None:
        smt = select(PaymentModel).where(PaymentModel.idempotency_key == key)
        return (await self.session.execute(smt)).scalar_one_or_none()
