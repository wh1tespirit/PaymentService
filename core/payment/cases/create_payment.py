from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import ApiExceptionCode, AppError
from core.outbox.models import OutboxModel
from core.payment.dto.create_payment import CreatePaymentDTO
from core.payment.dto.events import PaymentCreatedEvent
from core.payment.enums import OutboxEventType
from core.payment.models import PaymentModel


class CreatePaymentCase:
    """Создаёт платёж и outbox-событие в одной транзакции (Outbox pattern).

    Идемпотентность: повтор с известным idempotency_key возвращает исходный
    платёж, тот же ключ с другим телом — конфликт. Гонка параллельных запросов
    разрешается unique constraint'ом, поэтому вся вставка (включая flush,
    на котором и срабатывает констрейнт) обёрнута в try/except.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, dto: CreatePaymentDTO) -> PaymentModel:
        existing = await self._get_by_idempotency_key(dto.idempotency_key)
        if existing:
            return self._ensure_same_payload(existing, dto)

        payment = PaymentModel(
            amount=dto.amount,
            currency=dto.currency,
            description=dto.description,
            metadata_=dto.metadata,
            idempotency_key=dto.idempotency_key,
            webhook_url=dto.webhook_url,
        )
        try:
            self.session.add(payment)
            await self.session.flush()
            self.session.add(
                OutboxModel(
                    event_type=OutboxEventType.PAYMENT_CREATED,
                    payload=PaymentCreatedEvent(payment_id=payment.id).md(),
                )
            )
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self._get_by_idempotency_key(dto.idempotency_key)
            if existing is None:
                raise
            return self._ensure_same_payload(existing, dto)
        return payment

    async def _get_by_idempotency_key(self, key: str) -> PaymentModel | None:
        smt = select(PaymentModel).where(PaymentModel.idempotency_key == key)
        return (await self.session.execute(smt)).scalar_one_or_none()

    @staticmethod
    def _ensure_same_payload(payment: PaymentModel, dto: CreatePaymentDTO) -> PaymentModel:
        """Ключ идемпотентности защищает от дублей, а не переиспользуется под новый платёж."""
        matches = (
            payment.amount == dto.amount
            and payment.currency == dto.currency
            and payment.description == dto.description
            and payment.metadata_ == dto.metadata
            and payment.webhook_url == dto.webhook_url
        )
        if not matches:
            raise AppError(
                message="Idempotency-Key already used with a different payload",
                api_code=ApiExceptionCode.Conflict,
                api_data={"payment_id": payment.id},
            )
        return payment
