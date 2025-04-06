from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from common.mongo.enums import Collections
from common.mongo.repositories.sample import SampleRepository


class MongoClient:
    client: AsyncIOMotorClient
    db: AsyncIOMotorDatabase

    samples: SampleRepository

    def __init__(self, uri: str, database: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[database]

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        self.samples = SampleRepository(self.db[Collections.SAMPLE])

    async def close(self):
        self.client.close()
