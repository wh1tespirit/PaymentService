from api.core.dependencies.container import ContainerTypeDI
from api.routes.payments.schemas.payments_req import CreatePaymentReq
from api.routes.payments.schemas.payments_resp import PaymentCreatedResp
from core.payment.cases.create_payment import CreatePaymentCase
from core.payment.dto.create_payment import CreatePaymentDTO


async def create_payment(container: ContainerTypeDI, model: CreatePaymentReq, idempotency_key: str):
    case = await container.get(CreatePaymentCase)
    dto = CreatePaymentDTO(
        amount=model.amount,
        currency=model.currency,
        description=model.description,
        metadata=model.metadata,
        webhook_url=str(model.webhook_url),
        idempotency_key=idempotency_key,
    )
    payment = await case.execute(dto)
    return PaymentCreatedResp.model_validate(payment)
