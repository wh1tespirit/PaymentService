from common.pydantic.base import BaseModel


class CreateSampleRequest(BaseModel):
    name: str
    description: str
