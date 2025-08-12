from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.dependencies.container import ContainerTypeDI
from api.core.schemas import PaginatorReq, PaginatorResp
from api.routes.samples.schemas.samples_resp import SampleResp
from common.errors import ApiExceptionCode, AppError
from core.samples.models import SampleModel


async def get_samples(container: ContainerTypeDI, paginator: PaginatorReq):
    session = await container.get(AsyncSession)
    total = (await session.execute(select(func.count(SampleModel.id)))).scalar_one()
    samples = (
        (await session.execute(select(SampleModel).offset(paginator.offset).limit(paginator.limit))).scalars().all()
    )
    return PaginatorResp.response(
        items=[SampleResp.model_validate(sample) for sample in samples],
        total=total,
        limit=paginator.limit,
        offset=paginator.offset,
    )


async def get_sample(container: ContainerTypeDI, sample_id: str):
    session = await container.get(AsyncSession)
    sample = (await session.execute(select(SampleModel).where(SampleModel.id == sample_id))).scalar_one_or_none()
    if not sample:
        raise AppError(
            message="Sample not found",
            api_code=ApiExceptionCode.ObjectNotFound,
            api_data={"sample_id": sample_id},
        )
    return SampleResp.model_validate(sample)
