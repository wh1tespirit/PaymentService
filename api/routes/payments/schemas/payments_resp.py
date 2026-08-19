from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from common.pydantic.base import BaseModel
from core.payment.enums import Currency, PaymentStatus


class PaymentCreatedResp(BaseModel):
    payment_id: str = Field(validation_alias="id")
    status: PaymentStatus
    created_at: datetime


class PaymentResp(BaseModel):
    payment_id: str = Field(validation_alias="id")
    amount: Decimal
    currency: Currency
    description: str | None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_")
    status: PaymentStatus
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
