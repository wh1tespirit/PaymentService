from collections.abc import Awaitable, Callable

from faststream.rabbit import RabbitBroker

from common.broker import PAYMENTS_EXCHANGE, ROUTING_KEY
from core.outbox.errors import UnknownOutboxEventTypeError
from core.outbox.models import OutboxModel
from core.payment.enums import OutboxEventType

ROUTING_KEY_BY_EVENT = {OutboxEventType.PAYMENT_CREATED: ROUTING_KEY}


def make_publisher(broker: RabbitBroker) -> Callable[[OutboxModel], Awaitable[None]]:
    """Публикует outbox-событие по routing key его типа.

    Незарегистрированный тип — ошибка, а не публикация «куда-нибудь»: пачка
    откатится и событие останется pending. Отправить событие в чужую очередь
    тихо и необратимо хуже, чем упасть в лог.
    """

    async def publish(event: OutboxModel) -> None:
        routing_key = ROUTING_KEY_BY_EVENT.get(event.event_type)
        if routing_key is None:
            raise UnknownOutboxEventTypeError(f"No routing key for outbox event type {event.event_type!r}")
        await broker.publish(
            event.payload,
            exchange=PAYMENTS_EXCHANGE,
            routing_key=routing_key,
            persist=True,
        )

    return publish
