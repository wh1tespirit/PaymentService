import logging

from faststream import FastStream
from faststream.rabbit.annotations import RabbitMessage

from common.broker import PAYMENTS_EXCHANGE, PAYMENTS_QUEUE, create_broker, declare_topology
from common.container import Container
from common.logger import Loggers, setup_console_logger
from consumer.retry import read_attempt, route_failure
from core.payment.cases.process_payment import ProcessPaymentCase
from core.payment.dto.events import PaymentCreatedEvent

setup_console_logger(Loggers.CONSUMER_CONSOLE)
logger = logging.getLogger(Loggers.CONSUMER_CONSOLE)

broker = create_broker()
app = FastStream(broker)


@app.after_startup
async def setup_topology() -> None:
    await declare_topology(broker)


@app.on_shutdown
async def close_container() -> None:
    await Container.close()


@broker.subscriber(PAYMENTS_QUEUE, PAYMENTS_EXCHANGE)
async def handle_payment_created(event: PaymentCreatedEvent, message: RabbitMessage) -> None:
    """Единственный обработчик: эмуляция шлюза, статус в БД, webhook.

    Ошибка обработки уходит в route_failure (retry/DLQ), после чего сообщение
    подтверждается. Если сломается сама публикация в retry, исключение выйдет
    из обработчика: FastStream отклонит сообщение без requeue, и DLX основной
    очереди отправит его в DLQ — событие останется видимым, а не потеряется.
    """
    attempt = read_attempt(message.headers)
    try:
        async with Container() as container:
            case = await container.get(ProcessPaymentCase)
            payment = await case.execute(event.payment_id)
        logger.info(f"Payment {event.payment_id} processed: {payment.status}")
    except Exception:
        logger.exception(f"Processing failed for payment {event.payment_id} (attempt {attempt})")
        await route_failure(broker, event.md(), attempt)
