import os

from .common import *  # noqa: F403, F405

DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1")

SECRET_KEY = os.environ.get("SECRET_KEY", "default-insecure-prod-key")

ALLOWED_HOSTS = [
    "dicoevent-production.up.railway.app",
    ".railway.app",
    "127.0.0.1",
    "localhost",
]

extra_hosts = os.getenv("ALLOWED_HOSTS", "")
if extra_hosts:
    ALLOWED_HOSTS.extend([h.strip() for h in extra_hosts.split(",") if h.strip()])

STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

CSRF_TRUSTED_ORIGINS = [
    "https://dicoevent-production.up.railway.app",
    "https://*.railway.app",
    "https://*.up.railway.app",
]

extra_trusted = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if extra_trusted:
    CSRF_TRUSTED_ORIGINS.extend([origin.strip() for origin in extra_trusted.split(",") if origin.strip()])
