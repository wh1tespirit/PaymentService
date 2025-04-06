from common.mongo.models.base import MongoBaseModelWithDT


class SampleModel(MongoBaseModelWithDT):
    name: str
    description: str
