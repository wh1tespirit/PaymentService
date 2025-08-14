from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.dependencies.container import ContainerTypeDI
from api.core.schemas import PaginatorReq, PaginatorResp
from api.routes.samples.schemas.samples_req import CreateSampleReq
from api.routes.samples.schemas.samples_resp import SampleResp
from common.errors import ApiExceptionCode, AppError
from core.sample.cases.create_sample import CreateSampleCase
from core.sample.dto.create_sample import CreateSampleDTO
from core.sample.models import SampleModel


async def get_samples(container: ContainerTypeDI, paginator: PaginatorReq):
    session = await container.get(AsyncSession)

    count_smt = select(func.count(SampleModel.id))
    samples_smt = select(SampleModel).offset(paginator.offset).limit(paginator.limit)
    total = (await session.execute(count_smt)).scalar_one()
    samples = (await session.execute(samples_smt)).scalars().all()
    return PaginatorResp.response(
        items=[SampleResp.model_validate(sample) for sample in samples],
        total=total,
        limit=paginator.limit,
        offset=paginator.offset,
    )


async def get_sample(container: ContainerTypeDI, sample_id: str):
    session = await container.get(AsyncSession)
    smt = select(SampleModel).where(SampleModel.id == sample_id)
    sample = (await session.execute(smt)).scalar_one_or_none()
    if not sample:
        raise AppError(
            message="Sample not found",
            api_code=ApiExceptionCode.ObjectNotFound,
            api_data={"sample_id": sample_id},
        )
    return SampleResp.model_validate(sample)


async def create_sample(container: ContainerTypeDI, model: CreateSampleReq):
    create_sample = await container.get(CreateSampleCase)
    sample = await create_sample.execute(CreateSampleDTO.model_validate(model))
    return SampleResp.model_validate(sample)
