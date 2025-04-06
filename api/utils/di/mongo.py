from common import settings
from common.mongo.client import MongoClient


async def get_mongo_client_di():
    async with MongoClient(settings.MONGO_URI, settings.MONGO_DB) as client:
        yield client
