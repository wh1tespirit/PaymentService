from pydantic import Field, HttpUrl

from core.payment.dto.create_payment import PaymentPayload


class CreatePaymentReq(PaymentPayload):
    webhook_url: HttpUrl = Field(description="URL для уведомления о результате")
