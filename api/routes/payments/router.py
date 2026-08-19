from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Header

from api.core.dependencies.auth import AuthApiKeyDI
from api.core.dependencies.container import ContainerTypeDI
from api.core.enums import Tags
from api.routes.payments.schemas.payments_req import CreatePaymentReq
from api.routes.payments.schemas.payments_resp import PaymentCreatedResp

from . import controller

router = APIRouter(prefix="/api/v1/payments", tags=[Tags.PAYMENTS], dependencies=[AuthApiKeyDI])

ROOT = ""


@router.post(ROOT, response_model=PaymentCreatedResp, status_code=HTTPStatus.ACCEPTED)
async def create_payment(
    container: ContainerTypeDI,
    model: CreatePaymentReq,
    idempotency_key: Annotated[str, Header(min_length=1)],
):
    return await controller.create_payment(container, model, idempotency_key)
