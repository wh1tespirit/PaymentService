from faststream.rabbit import RabbitBroker

from common.broker import DLQ_NAME, MAX_ATTEMPTS, retry_queue_name


async def route_failure(broker: RabbitBroker, payload: dict, attempt: int) -> None:
    """Маршрутизирует упавшее сообщение: retry с экспоненциальной задержкой или DLQ.

    attempt — число уже сделанных ретраев (из заголовка x-attempt, 0 при
    первой доставке). Публикация идёт через default exchange по имени
    очереди; из retry-очереди сообщение вернётся в payments.new через DLX.
    """
    if attempt >= MAX_ATTEMPTS:
        await broker.publish(
            payload,
            queue=DLQ_NAME,
            headers={"x-attempt": attempt},
            persist=True,
        )
        return

    next_attempt = attempt + 1
    await broker.publish(
        payload,
        queue=retry_queue_name(next_attempt),
        headers={"x-attempt": next_attempt},
        persist=True,
    )
