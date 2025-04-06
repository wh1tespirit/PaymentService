from fastapi import APIRouter, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest

from api.services.metric.registry import REGISTRY
from api.utils.enums import Tags

router = APIRouter(prefix="/metrics", tags=[Tags.METRICS])


@router.get("/")
async def get_metrics(response: Response, request: Request):
    return PlainTextResponse(generate_latest(REGISTRY))
