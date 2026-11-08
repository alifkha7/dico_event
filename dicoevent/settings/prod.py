import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import MIDDLEWARE, configure_silk_middleware

DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
if DEBUG:
    raise ImproperlyConfigured("DEBUG must be False in production settings.")

SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
_INSECURE_KEYS = (
    "",
    "django-insecure-default-key-for-dev",
    "django-insecure-dicoevent-default-secret-key-change-in-production",
)
if not SECRET_KEY or SECRET_KEY in _INSECURE_KEYS or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("SECRET_KEY must be set to a secure, non-default value in production.")

_prod_hosts_env = os.environ.get("ALLOWED_HOSTS", "").strip()
ALLOWED_HOSTS = [h.strip() for h in _prod_hosts_env.split(",") if h.strip()]
if not ALLOWED_HOSTS or any("*" in h for h in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must be explicitly defined and cannot be empty or contain '*' in production."
    )

# Production security headers by default (overridable via explicit env vars for local testing)
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() in ("true", "1", "yes")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True").lower() in ("true", "1", "yes")
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "True").lower() in ("true", "1", "yes")
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", 31536000))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() in (
    "true",
    "1",
    "yes",
)
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "True").lower() in ("true", "1", "yes")

# Require explicit CORS_ALLOWED_ORIGINS without wildcard "*"
_cors_env = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
if _cors_env:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
elif "CORS_ALLOWED_ORIGINS" not in globals():
    CORS_ALLOWED_ORIGINS = []

CORS_ALLOW_ALL_ORIGINS = False
if "*" in CORS_ALLOWED_ORIGINS or any("*" in o for o in CORS_ALLOWED_ORIGINS):
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS cannot contain wildcard '*' in production.")

# Silk profiling defaults to False in production
ENABLE_SILK = os.environ.get("ENABLE_SILK", "False").lower() in ("true", "1", "yes")
MIDDLEWARE = configure_silk_middleware(ENABLE_SILK, MIDDLEWARE)
