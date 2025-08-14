from common.pydantic.base import BaseModel


class CreateSampleReq(BaseModel):
    name: str
    description: str | None = None
