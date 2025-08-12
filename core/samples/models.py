from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from common.models.base import BaseModel


class SampleModel(BaseModel):
    __tablename__ = "samples"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
