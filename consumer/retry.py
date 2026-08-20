from collections.abc import Mapping
from typing import Any

from faststream.rabbit import RabbitBroker

from common.broker import ATTEMPT_HEADER, DLQ_NAME, MAX_ATTEMPTS, retry_queue_name


def read_attempt(headers: Mapping[str, Any]) -> int:
    """Число уже сделанных ретраев (0 при первой доставке).

    Битый заголовок не должен ронять обработчик: сообщение с мусором в
    x-attempt лучше провести через полный цикл ретраев, чем потерять.
    """
    try:
        return int(headers.get(ATTEMPT_HEADER, 0))
    except (TypeError, ValueError):
        return 0


async def route_failure(broker: RabbitBroker, payload: dict, attempt: int) -> None:
    """Маршрутизирует упавшее сообщение: retry с экспоненциальной задержкой или DLQ.

    Публикация идёт через default exchange по имени очереди; из retry-очереди
    сообщение вернётся в payments.new через DLX.
    """
    exhausted = attempt >= MAX_ATTEMPTS
    next_attempt = attempt if exhausted else attempt + 1
    queue = DLQ_NAME if exhausted else retry_queue_name(next_attempt)

    await broker.publish(
        payload,
        queue=queue,
        headers={ATTEMPT_HEADER: next_attempt},
        persist=True,
    )
