from common.pydantic.base import BaseModel


class PaymentCreatedEvent(BaseModel):
    payment_id: str
