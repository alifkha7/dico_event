import importlib
import os
import sys

# Dynamic environment selection
# If DJANGO_ENV is explicitly set in the environment, use it.
# Otherwise, default to "test" if running under pytest/tests, or "dev" for general use.
if "DJANGO_ENV" in os.environ:
    DJANGO_ENV = os.environ["DJANGO_ENV"].strip().lower()
elif "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv) or "test" in sys.argv:
    DJANGO_ENV = "test"
else:
    DJANGO_ENV = "dev"

ENV_MODULE_MAP = {
    "dev": "dicoevent.settings.dev",
    "development": "dicoevent.settings.dev",
    "prod": "dicoevent.settings.prod",
    "production": "dicoevent.settings.prod",
    "test": "dicoevent.settings.test",
    "testing": "dicoevent.settings.test",
}

target_module_name = ENV_MODULE_MAP.get(DJANGO_ENV, "dicoevent.settings.dev")

# Reload base module if already imported to re-read updated environment variables
if "dicoevent.settings.base" in sys.modules:
    importlib.reload(sys.modules["dicoevent.settings.base"])
else:
    importlib.import_module("dicoevent.settings.base")

# Import or reload target environment submodule
if target_module_name in sys.modules:
    target_mod = importlib.reload(sys.modules[target_module_name])
else:
    target_mod = importlib.import_module(target_module_name)

# Export target module attributes into this package's namespace
for attr in dir(target_mod):
    if not attr.startswith("__"):
        globals()[attr] = getattr(target_mod, attr)
