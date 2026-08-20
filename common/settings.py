import os

from dotenv import load_dotenv

# Файл с дефолтами для локального запуска; в контейнерах переменные приходят
# из docker-compose и имеют приоритет — load_dotenv не перекрывает уже
# заданные переменные окружения.
load_dotenv(os.getenv("ENV_FILE", "envs/test.env"))

DEBUG = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}

PROJECT_NAME = os.getenv("PROJECT_NAME", "")
PROJECT_PATH = os.path.dirname(os.path.dirname(__file__))

DATABASE_URI = os.getenv("DATABASE_URI", "")

RABBITMQ_URI = os.getenv("RABBITMQ_URI", "")

# AUTH
API_KEY = os.getenv("API_KEY", "")
OPENAPI_TOKEN = os.getenv("OPENAPI_TOKEN", "")

# CONSUMER
WEBHOOK_TIMEOUT = float(os.getenv("WEBHOOK_TIMEOUT", 10))

# PAYMENT GATEWAY EMULATOR
GATEWAY_SUCCESS_RATE = float(os.getenv("GATEWAY_SUCCESS_RATE", 0.9))
GATEWAY_MIN_DELAY = float(os.getenv("GATEWAY_MIN_DELAY", 2))
GATEWAY_MAX_DELAY = float(os.getenv("GATEWAY_MAX_DELAY", 5))

# OUTBOX RELAY
OUTBOX_POLL_INTERVAL = float(os.getenv("OUTBOX_POLL_INTERVAL", 0.5))
OUTBOX_BATCH_SIZE = int(os.getenv("OUTBOX_BATCH_SIZE", 100))
