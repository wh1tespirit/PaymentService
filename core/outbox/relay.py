import asyncio
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy import select

from common import settings
from common.db.connect import Session
from common.logger import Loggers
from common.utils import now_utc
from core.outbox.enums import OutboxStatus
from core.outbox.models import OutboxModel

PublishFn = Callable[[OutboxModel], Awaitable[None]]

logger = logging.getLogger(Loggers.API_CONSOLE)


async def relay_pending_once(publish: PublishFn, batch_size: int) -> int:
    """Один проход relay: публикует pending-события и помечает их published.

    FOR UPDATE SKIP LOCKED позволяет запускать несколько экземпляров api
    без двойной обработки строк. Гарантия — at-least-once: при падении
    посреди пачки транзакция откатывается и уже опубликованные события
    уйдут повторно; дубли гасит идемпотентность консюмера.
    """
    async with Session() as session:
        smt = (
            select(OutboxModel)
            .where(OutboxModel.status == OutboxStatus.PENDING)
            .order_by(OutboxModel.created_at)
            .with_for_update(skip_locked=True)
            .limit(batch_size)
        )
        events = (await session.execute(smt)).scalars().all()
        for event in events:
            await publish(event)
            event.status = OutboxStatus.PUBLISHED
            event.published_at = now_utc()
        await session.commit()
        return len(events)


async def run_relay_loop(publish: PublishFn) -> None:
    while True:
        try:
            published = await relay_pending_once(publish, settings.OUTBOX_BATCH_SIZE)
        except Exception:
            logger.exception("Outbox relay iteration failed")
        else:
            # Пачка забита целиком — очередь ещё не разобрана, идём за следующей
            # без паузы, иначе темп разбора упирается в batch_size / poll_interval.
            if published == settings.OUTBOX_BATCH_SIZE:
                continue
        await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)
