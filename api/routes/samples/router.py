from typing import Annotated

from fastapi import APIRouter, Query

from api.core.dependencies.container import ContainerTypeDI
from api.core.enums import Tags
from api.core.schemas import ApiResponse, ApiResponseOk, PaginatorReq, PaginatorResp
from api.routes.samples.schemas.samples_req import CreateSampleReq
from api.routes.samples.schemas.samples_resp import SampleResp

from . import controller

router = APIRouter(prefix="/samples", tags=[Tags.SAMPLES])

ROOT = "/"
SAMPLE_ID = "/{sample_id}"


@router.get(ROOT, response_model=ApiResponseOk[PaginatorResp[SampleResp]])
async def get_samples(container: ContainerTypeDI, paginator: Annotated[PaginatorReq, Query()]):
    samples = await controller.get_samples(container, paginator)
    return ApiResponse.ok(samples)


@router.post(ROOT, response_model=ApiResponseOk[SampleResp])
async def create_sample(container: ContainerTypeDI, model: CreateSampleReq):
    sample = await controller.create_sample(container, model)
    return ApiResponse.ok(sample)


@router.get(SAMPLE_ID, response_model=ApiResponseOk[SampleResp])
async def get_sample(container: ContainerTypeDI, sample_id: str):
    sample = await controller.get_sample(container, sample_id)
    return ApiResponse.ok(sample)
