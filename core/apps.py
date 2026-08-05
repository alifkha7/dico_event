from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core app.

    This app contains the custom user model and user/role management
    functionality for the event project.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'