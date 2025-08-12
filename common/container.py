import importlib
import pkgutil
from pathlib import Path

from dishka import make_async_container


def collect_providers():
    providers = []
    core_path = Path(__file__).parent.parent / "core"

    for module_info in pkgutil.iter_modules([str(core_path)]):
        try:
            module = importlib.import_module(f"core.{module_info.name}.providers")
            if hasattr(module, "providers"):
                providers.extend(module.providers)
        except ImportError:
            continue  # Модуль без провайдеров

    return providers


Container = make_async_container(*collect_providers())
