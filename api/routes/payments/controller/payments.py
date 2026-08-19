from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.dependencies.container import ContainerTypeDI
from api.routes.payments.schemas.payments_req import CreatePaymentReq
from api.routes.payments.schemas.payments_resp import PaymentCreatedResp, PaymentResp
from common.errors import ApiExceptionCode, AppError
from core.payment.cases.create_payment import CreatePaymentCase
from core.payment.dto.create_payment import CreatePaymentDTO
from core.payment.models import PaymentModel


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


async def get_payment(container: ContainerTypeDI, payment_id: str):
    session = await container.get(AsyncSession)
    smt = select(PaymentModel).where(PaymentModel.id == payment_id)
    payment = (await session.execute(smt)).scalar_one_or_none()
    if not payment:
        raise AppError(
            message="Payment not found",
            api_code=ApiExceptionCode.ObjectNotFound,
            api_data={"payment_id": payment_id},
        )
    return PaymentResp.model_validate(payment)
