from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from common import settings

EXCHANGE_NAME = "payments"
QUEUE_NAME = "payments.new"
ROUTING_KEY = QUEUE_NAME
DLQ_NAME = "payments.new.dlq"
DLQ_ROUTING_KEY = DLQ_NAME

# Заголовок с номером попытки: пишет route_failure, читает обработчик.
ATTEMPT_HEADER = "x-attempt"

RETRY_DELAYS_MS = [2000, 4000, 8000]
MAX_ATTEMPTS = len(RETRY_DELAYS_MS)

PAYMENTS_EXCHANGE = RabbitExchange(EXCHANGE_NAME, type=ExchangeType.DIRECT, durable=True)

# DLX на основной очереди: ack-политика FastStream по умолчанию —
# REJECT_ON_ERROR, то есть reject без requeue. Без dead-letter-exchange такое
# сообщение исчезло бы совсем (нечитаемое тело, падение самой публикации в
# retry), поэтому отклонённое сообщение уезжает в DLQ.
PAYMENTS_QUEUE = RabbitQueue(
    QUEUE_NAME,
    durable=True,
    routing_key=ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": EXCHANGE_NAME,
        "x-dead-letter-routing-key": DLQ_ROUTING_KEY,
    },
)


def retry_queue_name(attempt: int) -> str:
    return f"{QUEUE_NAME}.retry.{attempt}"


# Retry-очереди без консюмера: сообщение лежит в них TTL миллисекунд,
# затем через dead-letter-exchange возвращается в основную очередь.
RETRY_QUEUES = [
    RabbitQueue(
        retry_queue_name(attempt),
        durable=True,
        arguments={
            "x-message-ttl": ttl_ms,
            "x-dead-letter-exchange": EXCHANGE_NAME,
            "x-dead-letter-routing-key": ROUTING_KEY,
        },
    )
    for attempt, ttl_ms in enumerate(RETRY_DELAYS_MS, start=1)
]

DLQ = RabbitQueue(DLQ_NAME, durable=True, routing_key=DLQ_ROUTING_KEY)


def create_broker() -> RabbitBroker:
    return RabbitBroker(settings.RABBITMQ_URI)


async def declare_topology(broker: RabbitBroker) -> None:
    """Идемпотентно объявляет всю топологию; вызывается и relay, и консюмером.

    Binding основной очереди объявляется явно, чтобы публикации relay
    не терялись, если консюмер ещё не стартовал. DLQ забиндена под свой
    routing key — в неё приходят и явные публикации route_failure, и
    сообщения, отклонённые из основной очереди через DLX. Retry-очереди
    получают сообщения через default exchange (по имени очереди).
    """
    exchange = await broker.declare_exchange(PAYMENTS_EXCHANGE)

    main_queue = await broker.declare_queue(PAYMENTS_QUEUE)
    await main_queue.bind(exchange, routing_key=ROUTING_KEY)

    dlq = await broker.declare_queue(DLQ)
    await dlq.bind(exchange, routing_key=DLQ_ROUTING_KEY)

    for queue in RETRY_QUEUES:
        await broker.declare_queue(queue)
