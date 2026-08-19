import pytest
from sqlalchemy import select

from common.db.connect import Session
from core.outbox.enums import OutboxStatus
from core.outbox.models import OutboxModel
from core.outbox.relay import relay_pending_once
from tests.factories import create_outbox_event


async def get_all_events() -> list[OutboxModel]:
    async with Session() as session:
        return list((await session.execute(select(OutboxModel))).scalars())


async def test_relay_publishes_pending_and_marks_published():
    await create_outbox_event("p-1")
    await create_outbox_event("p-2")
    published = []

    async def publish(event: OutboxModel) -> None:
        published.append(event.payload["payment_id"])

    count = await relay_pending_once(publish, batch_size=10)

    assert count == 2
    assert sorted(published) == ["p-1", "p-2"]
    events = await get_all_events()
    assert all(e.status == OutboxStatus.PUBLISHED for e in events)
    assert all(e.published_at is not None for e in events)


async def test_relay_skips_already_published():
    await create_outbox_event("p-1")

    async def publish(event: OutboxModel) -> None:
        pass

    assert await relay_pending_once(publish, batch_size=10) == 1
    assert await relay_pending_once(publish, batch_size=10) == 0


async def test_relay_keeps_pending_on_publish_error():
    await create_outbox_event("p-1")

    async def publish(event: OutboxModel) -> None:
        raise RuntimeError("broker down")

    with pytest.raises(RuntimeError):
        await relay_pending_once(publish, batch_size=10)

    events = await get_all_events()
    assert events[0].status == OutboxStatus.PENDING
