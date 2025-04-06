import os
from datetime import timedelta

from dotenv import load_dotenv

DEBUG = True

if DEBUG:
    load_dotenv("./common/global_configs/test.env")
else:
    load_dotenv("./common/global_configs/prod.env")

PROJECT_NAME = os.getenv("PROJECT_NAME", "")
PROJECT_PATH = os.path.dirname(os.path.dirname(__file__))

# # MONGO CONNECTION
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "")


DEFAULT_LOCALE = "ru"

# PROMETHEUS
PROMETHEUS_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "")

# REDIS
REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# AUTH
SOME_ADMIN_TOKEN = os.getenv("SOME_ADMIN_TOKEN", "")

# CACHE
CACHE_EXPIRE_TIME = timedelta(minutes=2)
