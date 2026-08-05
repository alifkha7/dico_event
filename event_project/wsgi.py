"""WSGI config for event_project project.

This file contains the WSGI application used by Django's development
and production servers. It exposes the WSGI callable as a module-level
variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "event_project.settings.dev")

application = get_wsgi_application()
