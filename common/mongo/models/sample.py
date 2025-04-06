from common.mongo.models.base import BaseMongoModelWithDT


class SampleModel(BaseMongoModelWithDT):
    name: str
    description: str
