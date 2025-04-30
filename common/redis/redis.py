from datetime import timedelta

from redis.asyncio import Redis

from common.redis.errors import RedisConnectionError, RedisSetError


class RedisService:
    def __init__(self, host: str, password: str | None = None, port: int = 6379):
        self.__client = Redis(
            host=host,
            password=password,
            port=port,
        )

    async def connect(self):
        result = await self.__client.ping()
        if not result:
            raise RedisConnectionError

    async def close(self):
        await self.__client.close()

    async def set(self, key: str, value: str | bytes, expire: timedelta | None = None, nx: bool = False):
        result = await self.__client.set(key, value, ex=expire, nx=nx)
        if not result:
            raise RedisSetError(key, value)

    async def get(self, key: str) -> str | bytes | None:
        return await self.__client.get(key)

    async def delete(self, key: str) -> int:
        return await self.__client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.__client.exists(key)

    async def scan(self, pattern: str) -> list[bytes]:
        result = await self.__client.scan(match=pattern)
        return result[1]

    async def delete_many(self, keys: list[str] | list[bytes]):
        if not keys:
            return
        return await self.__client.delete(*keys)
