from fastapi import APIRouter, Request

from api.routes.sample import controller
from api.routes.sample.schemas.req import CreateSampleRequest
from api.routes.sample.schemas.resp import SampleResp
from api.utils.di import IsAdminDI, MongoTypeDI
from api.utils.enums import Tags
from api.utils.response import ApiResponse, ApiResponseOk

ROOT = "/samples"

router = APIRouter(prefix=ROOT, tags=[Tags.SAMPLE])


@router.get("/", response_model=ApiResponseOk[list[SampleResp]])
async def get_samples(mongo: MongoTypeDI, request: Request):
    result = await controller.get_samples(mongo)
    return ApiResponse.ok(result)


@router.post("/", response_model=ApiResponseOk[SampleResp], dependencies=[IsAdminDI])
async def create_sample(payload: CreateSampleRequest, mongo: MongoTypeDI):
    result = await controller.create_sample(payload, mongo)
    return ApiResponse.ok(result)
