from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from common.utils import generate_uuid, now_utc


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=generate_uuid,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
    )
