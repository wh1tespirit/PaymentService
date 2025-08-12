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


DEFAULT_LOCALE = "ru"

# PROMETHEUS
PROMETHEUS_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "")

# REDIS
REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")


# OPENAPI
OPENAPI_TOKEN = os.getenv("OPENAPI_TOKEN", "")
