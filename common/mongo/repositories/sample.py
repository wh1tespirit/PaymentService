from common.mongo.models.sample import SampleModel
from common.mongo.repositories.base import BaseCachedRepository


class SampleRepository(BaseCachedRepository[SampleModel]):
    model = SampleModel
