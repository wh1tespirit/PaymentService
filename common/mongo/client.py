from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from common import settings
from common.mongo.enums import Collections
from common.mongo.repositories.sample import SampleRepository
from common.redis.redis import RedisService


class MongoClient:
    client: AsyncIOMotorClient
    db: AsyncIOMotorDatabase

    samples: SampleRepository

    def __init__(self, uri: str, database: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[database]
        self.__cache = RedisService(settings.REDIS_HOST, settings.REDIS_PASSWORD, settings.REDIS_PORT)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        self.samples = SampleRepository(self.db[Collections.SAMPLE], self.__cache)

    async def close(self):
        self.client.close()
