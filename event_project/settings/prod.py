import os

from .common import *  # noqa: F403

DEBUG = False

SECRET_KEY = os.environ.get("SECRET_KEY", "default-insecure-prod-key")

ALLOWED_HOSTS = ["127.0.0.1"]
