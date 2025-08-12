from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from scalar_fastapi import get_scalar_api_reference
from starlette.responses import JSONResponse

from api.core.dependencies.auth import AuthTokenQueryDI, AuthTokenQueryDIType
from api.core.enums import Tags
from common import settings

PREFIX = "/docs"

router = APIRouter(prefix=PREFIX, tags=[Tags.DOCS], dependencies=[AuthTokenQueryDI])


@router.get("/", include_in_schema=False)
async def docs(token: AuthTokenQueryDIType):
    return get_swagger_ui_html(
        openapi_url=f"{PREFIX}/openapi.json?token={token}",
        title=settings.PROJECT_NAME,
        swagger_ui_parameters={
            "operationsSorter": "alpha",
            "tagsSorter": "alpha",
            "docExpansion": "none",
        },
    )


@router.get("/scalar", include_in_schema=False)
async def scalar_html(token: AuthTokenQueryDIType):
    return get_scalar_api_reference(openapi_url=f"{PREFIX}/openapi.json?token={token}", title=settings.PROJECT_NAME)


@router.get("/openapi.json", include_in_schema=False)
async def openapi_json(request: Request):
    return JSONResponse(request.app.openapi())
