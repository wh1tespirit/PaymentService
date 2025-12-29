
from dishka import make_async_container

from common.utils import collect_providers, import_all_models

import_all_models()

Container = make_async_container(*collect_providers())
