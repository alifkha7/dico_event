import importlib
import os

# Dynamic environment selection routed purely via DJANGO_ENV
DJANGO_ENV = os.environ.get("DJANGO_ENV", "dev").strip().lower()

ENV_MODULE_MAP = {
    "dev": "dicoevent.settings.dev",
    "development": "dicoevent.settings.dev",
    "prod": "dicoevent.settings.prod",
    "production": "dicoevent.settings.prod",
    "test": "dicoevent.settings.test",
    "testing": "dicoevent.settings.test",
}

target_module_name = ENV_MODULE_MAP.get(DJANGO_ENV, "dicoevent.settings.dev")

# Reload base module to re-read updated environment variables
base_mod = importlib.import_module("dicoevent.settings.base")
importlib.reload(base_mod)

# Import or reload target environment submodule
target_mod = importlib.import_module(target_module_name)
importlib.reload(target_mod)

# Export target module attributes into this package's namespace
for attr in dir(target_mod):
    if not attr.startswith("__"):
        globals()[attr] = getattr(target_mod, attr)
