from common.mongo.models.sample import SampleModel
from common.mongo.repositories.base import BaseUpdateRepository


class SampleRepository(BaseUpdateRepository[SampleModel]):
    model = SampleModel
