from arq.connections import RedisSettings

from common import settings

REDIS_SETTINGS = RedisSettings(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD)
