from datetime import datetime

from pydantic import Field

from common.pydantic.base import BaseModel as PydanticBaseModel
from common.utils import generate_object_id, get_utc_datetime


class BaseMongoModel(PydanticBaseModel):
    id: str = Field(default_factory=generate_object_id, alias="_id")

    def to_upt(self, exclude: set[str] | None = None):
        if exclude is None:
            exclude = {"id"}

        return self.md(exclude=exclude)

    def upt_from_dict(self, data: dict):
        for key, value in data.items():
            if not hasattr(self, key):
                continue
            setattr(self, key, value)


class BaseMongoModelWithDT(BaseMongoModel):
    created_at: datetime = Field(default_factory=get_utc_datetime, description="Дата создания")
    updated_at: datetime = Field(default_factory=get_utc_datetime, description="Дата обновления")

    def to_upt(self, exclude: set[str] | None = None):
        if exclude is None:
            exclude = {"id", "created_at"}

        self.updated_at = get_utc_datetime()
        return super().to_upt(exclude)
