import pytest

from common.db.connect import Session
from core.payment.cases.process_payment import ProcessPaymentCase
from core.payment.enums import PaymentStatus
from core.payment.errors import PaymentProcessingError, WebhookDeliveryError
from core.payment.models import PaymentModel
from tests.factories import create_pending_payment


class RecordingGateway:
    def __init__(self, result: PaymentStatus):
        self.result = result
        self.calls = 0

    async def process(self, payment: PaymentModel) -> PaymentStatus:
        self.calls += 1
        return self.result


class RecordingWebhook:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[str] = []

    async def send(self, payment: PaymentModel) -> None:
        if self.fail:
            raise WebhookDeliveryError("webhook unavailable")
        self.sent.append(payment.id)


async def run_case(payment_id: str, gateway, webhook) -> PaymentModel:
    async with Session() as session:
        case = ProcessPaymentCase(session, gateway, webhook)
        return await case.execute(payment_id)


async def get_payment(payment_id: str) -> PaymentModel:
    async with Session() as session:
        return await session.get_one(PaymentModel, payment_id)


async def test_success_updates_status_and_sends_webhook():
    payment = await create_pending_payment()
    gateway = RecordingGateway(PaymentStatus.SUCCEEDED)
    webhook = RecordingWebhook()

    await run_case(payment.id, gateway, webhook)

    stored = await get_payment(payment.id)
    assert stored.status == PaymentStatus.SUCCEEDED
    assert stored.processed_at is not None
    assert webhook.sent == [payment.id]


async def test_gateway_failure_is_business_result_not_error():
    payment = await create_pending_payment()
    gateway = RecordingGateway(PaymentStatus.FAILED)
    webhook = RecordingWebhook()

    await run_case(payment.id, gateway, webhook)

    stored = await get_payment(payment.id)
    assert stored.status == PaymentStatus.FAILED
    assert webhook.sent == [payment.id]


async def test_redelivery_skips_gateway_but_resends_webhook():
    payment = await create_pending_payment()
    gateway = RecordingGateway(PaymentStatus.SUCCEEDED)
    webhook = RecordingWebhook()

    await run_case(payment.id, gateway, webhook)
    await run_case(payment.id, gateway, webhook)

    assert gateway.calls == 1
    assert webhook.sent == [payment.id, payment.id]


async def test_webhook_failure_raises_but_status_is_committed():
    payment = await create_pending_payment()
    gateway = RecordingGateway(PaymentStatus.SUCCEEDED)
    webhook = RecordingWebhook(fail=True)

    with pytest.raises(WebhookDeliveryError):
        await run_case(payment.id, gateway, webhook)

    stored = await get_payment(payment.id)
    assert stored.status == PaymentStatus.SUCCEEDED


async def test_unknown_payment_raises_processing_error():
    with pytest.raises(PaymentProcessingError):
        await run_case("no-such-id", RecordingGateway(PaymentStatus.SUCCEEDED), RecordingWebhook())
