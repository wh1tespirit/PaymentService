from unittest.mock import AsyncMock

import pytest

from common.broker import PAYMENTS_EXCHANGE
from core.outbox.errors import UnknownOutboxEventTypeError
from core.outbox.models import OutboxModel
from core.outbox.publisher import make_publisher


def make_event(event_type: str) -> OutboxModel:
    return OutboxModel(event_type=event_type, payload={"payment_id": "p-1"})


async def test_publishes_with_routing_key_of_event_type():
    broker = AsyncMock()

    await make_publisher(broker)(make_event("payment.created"))

    broker.publish.assert_awaited_once_with(
        {"payment_id": "p-1"},
        exchange=PAYMENTS_EXCHANGE,
        routing_key="payments.new",
        persist=True,
    )


async def test_unknown_event_type_is_not_published():
    """Незнакомый тип не должен уезжать в чужую очередь под видом payment.created."""
    broker = AsyncMock()

    with pytest.raises(UnknownOutboxEventTypeError):
        await make_publisher(broker)(make_event("payment.refunded"))

    broker.publish.assert_not_awaited()
