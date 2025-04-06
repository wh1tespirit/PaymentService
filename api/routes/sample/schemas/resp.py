from pydantic import Field

from common.mongo.models.sample import SampleModel
from common.utils import generate_object_id


class SampleResp(SampleModel):
    id: str = Field(default_factory=generate_object_id)
