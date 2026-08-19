from decimal import Decimal
from typing import Any

from pydantic import Field

from common.pydantic.base import BaseModel
from core.payment.enums import Currency


class CreatePaymentDTO(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: Currency
    description: str | None = None
    metadata: dict[str, Any] | None = None
    webhook_url: str
    idempotency_key: str
