"""ASGI config for event_project project.

It exposes the ASGI callable as a module-level variable named
``application``. Django's default ASGI configuration suffices here.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "event_project.settings.dev")

application = get_asgi_application()
