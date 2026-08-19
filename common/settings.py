import os

from dotenv import load_dotenv

DEBUG = True

if DEBUG:
    load_dotenv("envs/test.env")
else:
    load_dotenv("envs/prod.env")

PROJECT_NAME = os.getenv("PROJECT_NAME", "")
PROJECT_PATH = os.path.dirname(os.path.dirname(__file__))

DATABASE_URI = os.getenv("DATABASE_URI", "")

RABBITMQ_URI = os.getenv("RABBITMQ_URI", "")

# AUTH
API_KEY = os.getenv("API_KEY", "")
OPENAPI_TOKEN = os.getenv("OPENAPI_TOKEN", "")

# CONSUMER
WEBHOOK_TIMEOUT = float(os.getenv("WEBHOOK_TIMEOUT", 10))

# OUTBOX RELAY
OUTBOX_POLL_INTERVAL = float(os.getenv("OUTBOX_POLL_INTERVAL", 0.5))
OUTBOX_BATCH_SIZE = int(os.getenv("OUTBOX_BATCH_SIZE", 100))
