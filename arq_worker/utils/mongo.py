from common import settings
from common.mongo.client import MongoClient


async def mongo_startup_handler(ctx: dict):
    mongo = MongoClient(settings.MONGO_URI, settings.MONGO_DB)
    await mongo.connect()
    ctx["mongo"] = mongo


async def mongo_shutdown_handler(ctx: dict):
    await ctx["mongo"].close()
