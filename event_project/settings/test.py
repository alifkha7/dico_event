"""Test-specific Django settings.

Inherits from dev.py and overrides settings that are not suitable
for automated testing (e.g., throttling, caching).
"""

from .dev import *  # noqa: F401, F403

# Disable throttling entirely during testing to prevent
# DRF's internal cache calls from interfering with test mocks.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

# Use in-memory cache for tests to avoid Redis dependency
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
