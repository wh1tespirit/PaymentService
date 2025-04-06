from arq_worker.utils.logging import with_logging
from arq_worker.utils.types import MongoArqContext


@with_logging
async def sample_task(ctx: MongoArqContext, message: str, **kwargs):
    print(message)
    mongo = ctx["mongo"]
    sample = await mongo.samples.find_one({})
    print(sample)
