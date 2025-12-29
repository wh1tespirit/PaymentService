import importlib
import pkgutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def generate_uuid():
    return uuid.uuid4().hex


def now_utc():
    return datetime.now(UTC)

def import_all_models():
    """Автоматически импортирует все модели из core/*/models.py"""
    core_path = Path(__file__).parent.parent / "core"

    for module_info in pkgutil.iter_modules([str(core_path)]):
        try:
            # Пытаемся импортировать models.py из каждого модуля
            importlib.import_module(f"core.{module_info.name}.models")
        except ImportError:
            # Модуль без models.py - пропускаем
            continue


def collect_providers() -> list[Any]:
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
