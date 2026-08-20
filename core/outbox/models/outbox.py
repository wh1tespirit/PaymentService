from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import BaseModel
from core.outbox.enums import OutboxStatus


class OutboxModel(BaseModel):
    __tablename__ = "outbox"

    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus, name="outbox_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=OutboxStatus.PENDING,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Частичный индекс под единственный горячий запрос relay: он покрывает и
    # фильтр по status, и сортировку по created_at, но растёт только на
    # неразобранных строках — published-строки в него не попадают.
    __table_args__ = (
        Index("ix_outbox_pending", "created_at", postgresql_where=text("status = 'pending'")),
    )
