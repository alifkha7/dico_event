import os

from .base import *  # noqa: F403
from .base import CACHES, CORS_ALLOWED_ORIGINS, DATABASES, MIDDLEWARE, configure_silk_middleware

DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")

ENABLE_SILK = os.environ.get("ENABLE_SILK", "False").lower() in ("true", "1", "yes")
MIDDLEWARE = configure_silk_middleware(ENABLE_SILK, MIDDLEWARE)

# Fast password hashing for test execution
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Eager Celery execution during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# In-memory SQLite & LocMemCache for fast local tests, or real PostgreSQL/Redis when USE_SQLITE_TEST=False
USE_SQLITE_TEST = os.environ.get("USE_SQLITE_TEST", "True").lower() in ("true", "1", "yes")

if USE_SQLITE_TEST:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
            "TIMEOUT": 3600,
        }
    }
else:
    # Preserve PostgreSQL DATABASES and django-redis CACHES configured in base.py
    DATABASES = DATABASES
    CACHES = CACHES

# Default test CORS allowed origins
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "https://app.dicoevent.com",
    ]

CORS_ALLOW_ALL_ORIGINS = False
