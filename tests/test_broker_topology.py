from common.broker import (
    DLQ,
    MAX_ATTEMPTS,
    PAYMENTS_EXCHANGE,
    PAYMENTS_QUEUE,
    RETRY_DELAYS_MS,
    RETRY_QUEUES,
    retry_queue_name,
)


def test_main_queue_and_exchange():
    assert PAYMENTS_EXCHANGE.name == "payments"
    assert PAYMENTS_QUEUE.name == "payments.new"
    assert PAYMENTS_QUEUE.durable is True


def test_main_queue_dead_letters_to_dlq():
    """Reject без requeue (дефолт FastStream) должен приводить в DLQ, а не в никуда."""
    assert PAYMENTS_QUEUE.arguments["x-dead-letter-exchange"] == "payments"
    assert PAYMENTS_QUEUE.arguments["x-dead-letter-routing-key"] == "payments.new.dlq"
    assert DLQ.routing_key == "payments.new.dlq"


def test_max_attempts_follows_retry_delays():
    assert MAX_ATTEMPTS == len(RETRY_DELAYS_MS) == len(RETRY_QUEUES)


def test_retry_queues_exponential_ttl_and_dlx():
    assert [q.name for q in RETRY_QUEUES] == [
        "payments.new.retry.1",
        "payments.new.retry.2",
        "payments.new.retry.3",
    ]
    assert [q.arguments["x-message-ttl"] for q in RETRY_QUEUES] == [2000, 4000, 8000]
    for queue in RETRY_QUEUES:
        assert queue.arguments["x-dead-letter-exchange"] == "payments"
        assert queue.arguments["x-dead-letter-routing-key"] == "payments.new"


def test_dlq():
    assert DLQ.name == "payments.new.dlq"
    assert retry_queue_name(2) == "payments.new.retry.2"
