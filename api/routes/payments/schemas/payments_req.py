from decimal import Decimal
from typing import Any

from pydantic import Field, HttpUrl

from common.pydantic.base import BaseModel
from core.payment.enums import Currency


class CreatePaymentReq(BaseModel):
    amount: Decimal = Field(gt=0, description="Сумма платежа")
    currency: Currency = Field(description="Валюта: RUB, USD или EUR")
    description: str | None = Field(default=None, description="Описание платежа")
    metadata: dict[str, Any] | None = Field(default=None, description="Произвольные метаданные")
    webhook_url: HttpUrl = Field(description="URL для уведомления о результате")
