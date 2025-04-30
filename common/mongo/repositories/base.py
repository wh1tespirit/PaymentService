import gzip
import pickle
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import DeleteOne, InsertOne, ReplaceOne, UpdateOne

from common import settings
from common.mongo.models.base import BaseMongoModel
from common.redis.redis import RedisService


class BaseCollectionRepository:
    c: AsyncIOMotorCollection

    def __init__(self, collection: AsyncIOMotorCollection):
        self.c = collection


class BaseUpdateRepository[T: BaseMongoModel](BaseCollectionRepository):
    model: type[T]

    async def update_one_by_model(self, model: T):
        await self.c.find_one_and_update(
            {"_id": model.id},
            {"$set": model.to_upt()},
            return_document=True,
        )

    async def update_one_by_query(self, query: dict, update: dict):
        updated = await self.c.find_one_and_update(query, update, return_document=True)
        return self.model(**updated) if updated else None

    async def update_many_by_models(self, models: list[T]):
        bulk_updates = [UpdateOne({"_id": model.id}, {"$set": model.to_upt()}) for model in models]
        await self.c.bulk_write(bulk_updates)

    async def update_many_by_query(self, query: dict, update: dict):
        await self.c.update_many(query, update)

    async def delete_one(self, query: dict):
        deleted = await self.c.delete_one(query)
        return deleted.deleted_count > 0

    async def delete_many(self, query: dict):
        deleted = await self.c.delete_many(query)
        return deleted.deleted_count > 0

    async def insert_one(self, model: T):
        inserted = await self.c.insert_one(model.md(by_alias=True))
        return inserted.inserted_id

    async def insert_many(self, models: list[T]):
        inserted = await self.c.insert_many([model.md(by_alias=True) for model in models])
        return inserted.inserted_ids

    async def bulk(self, bulk: list[UpdateOne] | list[DeleteOne] | list[InsertOne] | list[ReplaceOne]):
        await self.c.bulk_write(bulk)


class BaseRepository[T: BaseMongoModel](BaseUpdateRepository):
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

    async def aggregate(self, pipeline: list[dict]) -> list[Any]:
        return await self.c.aggregate(pipeline).to_list(length=None)


class BaseCachedRepository[T: BaseMongoModel](BaseUpdateRepository):
    """
    Базовый класс для кэширования запросов к MongoDB.
    Важно: если используете запросы обновления, через поле c (collection), тогда необходимо сбрасывать кэш вручную через метод clear_cache
    """

    cache: RedisService
    model: type[T]

    expire_time = settings.CACHE_EXPIRE_TIME

    def __init__(self, collection: AsyncIOMotorCollection, cache: RedisService):
        super().__init__(collection)
        self.cache = cache
        self.prefix = self.c.name

    async def clear_cache(self):
        keys = await self.cache.scan(f"{self.prefix}:*")
        await self.cache.delete_many(keys)

    async def create_key(self, method: str, **kwargs):
        return f"{self.prefix}:{method}:{kwargs}"

    async def get_cache(self, key: str) -> Any | None:
        cached = await self.cache.get(key)
        return await self.decode(cached) if cached else None

    async def set_cache(self, key: str, value: Any):
        await self.cache.set(key, await self.encode(value), self.expire_time)

    async def encode(self, value: Any):
        return gzip.compress(pickle.dumps(value))

    async def decode(self, value: Any):
        return pickle.loads(gzip.decompress(value))

    async def find_one(self, query: dict, use_cache: bool = False) -> T | None:
        cache_key = await self.create_key("find_one", query=query)

        if use_cache:
            result = await self.get_cache(cache_key)
            if result:
                return result

        result = await self.c.find_one(query)
        model = self.model(**result) if result else None

        if use_cache:
            await self.set_cache(cache_key, model)

        return model

    async def find_many(
        self,
        query: dict,
        sort: dict | None = None,
        limit: int | None = None,
        offset: int | None = None,
        use_cache: bool = False,
    ) -> list[T]:
        cache_key = await self.create_key("find_many", query=query, sort=sort, limit=limit, offset=offset)
        if use_cache:
            result = await self.get_cache(cache_key)
            if result:
                return result

        cursor = self.c.find(query, sort=sort)
        if limit:
            cursor = cursor.limit(limit)
        if offset:
            cursor = cursor.skip(offset)

        result = await cursor.to_list(length=None)

        model = [self.model(**item) for item in result]

        if use_cache:
            await self.set_cache(cache_key, model)

        return model

    async def aggregate(self, pipeline: list[dict], use_cache: bool = False) -> list[Any]:
        cache_key = await self.create_key("aggregate", pipeline=pipeline)

        if use_cache:
            result = await self.get_cache(cache_key)
            if result:
                return result

        result = await self.c.aggregate(pipeline).to_list(length=None)

        if use_cache:
            await self.set_cache(cache_key, result)

        return result

    async def update_one_by_model(self, model: T):
        await super().update_one_by_model(model)
        await self.clear_cache()

    async def update_one_by_query(self, query: dict, update: dict):
        updated = await super().update_one_by_query(query, update)
        await self.clear_cache()
        return updated

    async def update_many_by_models(self, models: list[T]):
        await super().update_many_by_models(models)
        await self.clear_cache()

    async def update_many_by_query(self, query: dict, update: dict):
        await super().update_many_by_query(query, update)
        await self.clear_cache()

    async def delete_one(self, query: dict):
        deleted = await super().delete_one(query)
        await self.clear_cache()
        return deleted

    async def delete_many(self, query: dict):
        deleted = await super().delete_many(query)
        await self.clear_cache()
        return deleted

    async def insert_one(self, model: T):
        inserted = await super().insert_one(model)
        await self.clear_cache()
        return inserted

    async def insert_many(self, models: list[T]):
        inserted = await super().insert_many(models)
        await self.clear_cache()
        return inserted

    async def bulk(self, bulk: list[UpdateOne] | list[DeleteOne] | list[InsertOne] | list[ReplaceOne]):
        await super().bulk(bulk)
        await self.clear_cache()
