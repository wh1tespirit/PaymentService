from unittest.mock import AsyncMock

from consumer.retry import read_attempt, route_failure


def test_read_attempt_defaults_to_zero_and_survives_garbage():
    assert read_attempt({}) == 0
    assert read_attempt({"x-attempt": 2}) == 2
    assert read_attempt({"x-attempt": "не число"}) == 0
    assert read_attempt({"x-attempt": None}) == 0


async def test_first_failure_goes_to_retry_1():
    broker = AsyncMock()
    await route_failure(broker, {"payment_id": "p-1"}, attempt=0)
    broker.publish.assert_awaited_once_with(
        {"payment_id": "p-1"},
        queue="payments.new.retry.1",
        headers={"x-attempt": 1},
        persist=True,
    )


async def test_second_failure_goes_to_retry_2():
    broker = AsyncMock()
    await route_failure(broker, {"payment_id": "p-1"}, attempt=1)
    broker.publish.assert_awaited_once_with(
        {"payment_id": "p-1"},
        queue="payments.new.retry.2",
        headers={"x-attempt": 2},
        persist=True,
    )


async def test_exhausted_attempts_go_to_dlq():
    broker = AsyncMock()
    await route_failure(broker, {"payment_id": "p-1"}, attempt=3)
    broker.publish.assert_awaited_once_with(
        {"payment_id": "p-1"},
        queue="payments.new.dlq",
        headers={"x-attempt": 3},
        persist=True,
    )
