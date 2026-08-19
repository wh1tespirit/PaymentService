import json
import logging
import logging.handlers
import traceback
from enum import StrEnum
from pathlib import Path

from common import settings
from common.utils import now_utc

# Logging Levels
# https://docs.python.org/3/library/logging.html#logging-levels


class Loggers(StrEnum):
    API_CONSOLE = "api_console"
    API_FILE = "api_file"
    CONSUMER_CONSOLE = "consumer_console"
    CONSUMER_FILE = "consumer_file"


class ServiceNames(StrEnum):
    API = "api"
    CONSUMER = "consumer"


class Formatters(StrEnum):
    JSON = "json"
    PLAIN = "plain"


def namer(default_name: str):
    base_filename, ext, date = default_name.split(".")
    return f"{base_filename}_{date}.{ext}"


def __get_file_formatters(service_name: ServiceNames, formatter: Formatters):
    if formatter == Formatters.PLAIN:
        return logging.Formatter("[log_start]\n%(message)s")
    else:
        return get_json_formatter(service_name)


def setup_console_logger(logger_name: Loggers):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] [%(asctime)s] [%(pathname)s]\n%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def setup_file_logger(
    logger_name: Loggers,
    service_name: ServiceNames,
    logs_directory: str,
    formatter: Formatters = Formatters.JSON,  # plain нужен только для middleware api
    when: str = "D",
    interval: int = 1,
    backup_count: int = 10,
):
    logs_dir = Path(logs_directory)
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        logs_dir / "logs.log",
        when=when,
        interval=interval,
        backupCount=backup_count,
    )
    file_handler.namer = namer
    file_handler.setFormatter(__get_file_formatters(service_name, formatter))
    logger.addHandler(file_handler)
    return logger


def get_json_formatter(service_name: ServiceNames):
    class JSONFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord):
            log_record: dict = {
                "date": now_utc().isoformat(),
                "project_name": settings.PROJECT_NAME,
                "service_name": service_name.value,
                "level": record.levelname,
                "message": record.getMessage(),
            }

            if record.args:
                log_record.update(record.args)  # type: ignore

            if record.exc_info:
                exc_type, exc_value, _ = record.exc_info
                log_record["exception"] = f"{exc_type.__name__}: {exc_value}"
                log_record["traceback"] = str(traceback.format_exc())

            return f"[log_start]\n{json.dumps(log_record, ensure_ascii=False)}"

    return JSONFormatter()
