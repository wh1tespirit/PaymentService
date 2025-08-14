from common.pydantic.base import BaseModel


class CreateSampleDTO(BaseModel):
    name: str
    description: str | None = None
