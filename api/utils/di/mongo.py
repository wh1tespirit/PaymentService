from common import settings
from common.mongo.client import MongoWorker


async def get_mongo_client_di():
    async with MongoWorker(settings.MONGO_URI, settings.MONGO_DB) as client:
        yield client
