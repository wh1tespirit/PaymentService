from datetime import datetime

from common.pydantic.base import BaseModel


class SampleResp(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
