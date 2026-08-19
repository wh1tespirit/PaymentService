from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, String
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
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
