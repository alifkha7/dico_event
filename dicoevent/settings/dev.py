import os

from .base import *  # noqa: F403
from .base import CORS_ALLOWED_ORIGINS, MIDDLEWARE, configure_silk_middleware

DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

_dev_hosts_env = os.environ.get("ALLOWED_HOSTS", "").strip()
if _dev_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in _dev_hosts_env.split(",") if h.strip()]
else:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]

ENABLE_SILK = os.environ.get("ENABLE_SILK", "True").lower() in ("true", "1", "yes")
MIDDLEWARE = configure_silk_middleware(ENABLE_SILK, MIDDLEWARE)

if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

CORS_ALLOW_ALL_ORIGINS = False
