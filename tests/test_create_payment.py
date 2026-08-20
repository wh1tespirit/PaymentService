import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from common.db.connect import Session
from common.errors import ApiExceptionCode, AppError
from core.outbox.models import OutboxModel
from core.payment.cases.create_payment import CreatePaymentCase
from core.payment.dto.create_payment import CreatePaymentDTO
from core.payment.models import PaymentModel


def make_dto(idempotency_key: str = "key-1", **overrides) -> CreatePaymentDTO:
    fields = {
        "amount": Decimal("100.50"),
        "currency": "RUB",
        "description": "Заказ №1",
        "metadata": {"order_id": 42},
        "webhook_url": "http://localhost:9000/webhook",
        "idempotency_key": idempotency_key,
        **overrides,
    }
    return CreatePaymentDTO(**fields)


async def run_case(dto: CreatePaymentDTO) -> PaymentModel:
    async with Session() as session:
        return await CreatePaymentCase(session).execute(dto)


async def count_rows(model) -> int:
    async with Session() as session:
        return (await session.execute(select(func.count(model.id)))).scalar_one()


async def test_concurrent_requests_with_same_key_create_one_payment():
    """Гонка двух параллельных запросов: оба проходят pre-check, конфликт ловит unique constraint."""
    first, second = await asyncio.gather(run_case(make_dto("race-key")), run_case(make_dto("race-key")))

    assert first.id == second.id
    assert await count_rows(PaymentModel) == 1
    assert await count_rows(OutboxModel) == 1


async def test_repeat_with_same_payload_returns_same_payment():
    first = await run_case(make_dto("key-1"))
    second = await run_case(make_dto("key-1"))

    assert first.id == second.id
    assert await count_rows(PaymentModel) == 1
    assert await count_rows(OutboxModel) == 1


async def test_repeat_with_different_payload_is_conflict():
    await run_case(make_dto("key-1", amount=Decimal("100.50")))

    with pytest.raises(AppError) as exc_info:
        await run_case(make_dto("key-1", amount=Decimal("999.00")))

    assert exc_info.value.api_code == ApiExceptionCode.Conflict
    assert await count_rows(PaymentModel) == 1
