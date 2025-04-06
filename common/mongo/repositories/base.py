from motor.motor_asyncio import AsyncIOMotorCollection

from common.mongo.models.base import MongoBaseModel


class BaseCollectionRepository:
    c: AsyncIOMotorCollection

    def __init__(self, collection: AsyncIOMotorCollection):
        self.c = collection


class BaseUpdateRepository[T: MongoBaseModel](BaseCollectionRepository):
    model: type[T]

    async def update_by_model(self, model: T):
        await self.c.find_one_and_update(
            {"_id": model.id},
            {"$set": model.to_upt()},
            return_document=True,
        )

    async def update_by_query(self, query: dict, update: dict):
        updated = await self.c.find_one_and_update(query, update, return_document=True)
        return self.model(**updated) if updated else None

    async def delete_one(self, query: dict):
        deleted = await self.c.delete_one(query)
        return deleted.deleted_count > 0

    async def insert(self, model: T):
        inserted = await self.c.insert_one(model.md(by_alias=True))
        return inserted.inserted_id

    model: type[T]

    def __init__(self, collection: AsyncIOMotorCollection):
        super().__init__(collection)

    async def find_one(self, query: dict) -> T | None:
        result = await self.c.find_one(query)
        return self.model(**result) if result else None

    async def find_many(
        self, query: dict, sort: dict | None = None, limit: int | None = None, offset: int | None = None
    ) -> list[T]:
        cursor = self.c.find(query, sort=sort)
        if limit:
            cursor = cursor.limit(limit)
        if offset:
            cursor = cursor.skip(offset)
        result = await cursor.to_list(length=None)
        return [self.model(**item) for item in result]
