from typing import Annotated

from fastapi import Depends

from api.utils.di.auth import is_admin_di
from api.utils.di.mongo import get_mongo_client_di
from common.mongo.client import MongoWorker

IsAdminDI = Depends(is_admin_di)
MongoDI = Depends(get_mongo_client_di)

IsAdminTypeDI = Annotated[str, IsAdminDI]
MongoTypeDI = Annotated[MongoWorker, MongoDI]
