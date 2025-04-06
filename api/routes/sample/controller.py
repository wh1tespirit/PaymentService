from api.routes.sample.schemas.req import CreateSampleRequest
from api.utils.di import MongoTypeDI
from common.mongo.models.sample import SampleModel


async def get_samples(mongo: MongoTypeDI):
    samples = await mongo.samples.find_many({})
    return samples


async def create_sample(payload: CreateSampleRequest, mongo: MongoTypeDI):
    sample = SampleModel(**payload.md())
    await mongo.samples.insert(sample)
    return sample
