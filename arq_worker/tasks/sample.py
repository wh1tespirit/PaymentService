from arq_worker.controllers.sample import sample_controller
from arq_worker.utils.logging import with_logging
from arq_worker.utils.types import ArqContext


@with_logging
async def sample_task(
    ctx: ArqContext,
):
    await sample_controller(ctx["container"])
