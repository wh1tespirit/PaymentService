import pytest
from sqlalchemy.exc import IntegrityError

from core.payment.enums import PaymentStatus
from tests.factories import create_pending_payment


async def test_payment_defaults():
    payment = await create_pending_payment()
    assert payment.id
    assert payment.status == PaymentStatus.PENDING
    assert payment.processed_at is None


async def test_idempotency_key_is_unique():
    await create_pending_payment(idempotency_key="dup-key")
    with pytest.raises(IntegrityError):
        await create_pending_payment(idempotency_key="dup-key")
