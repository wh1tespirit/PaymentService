from decimal import Decimal
from typing import Any

from pydantic import Field

from common.pydantic.base import BaseModel
from core.payment.enums import Currency


class PaymentPayload(BaseModel):
    """Общее тело платежа для API-схемы и DTO: правила валидации в одном месте.

    Границы amount повторяют колонку Numeric(12, 2): без них Postgres молча
    округлит лишние знаки, а слишком большое число уронит INSERT.
    """

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, description="Сумма платежа")
    currency: Currency = Field(description="Валюта: RUB, USD или EUR")
    description: str | None = Field(default=None, description="Описание платежа")
    metadata: dict[str, Any] | None = Field(default=None, description="Произвольные метаданные")


class CreatePaymentDTO(PaymentPayload):
    webhook_url: str
    idempotency_key: str
