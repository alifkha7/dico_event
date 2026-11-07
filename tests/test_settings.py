import importlib


def test_settings_reads_database_env_vars(monkeypatch):
    """Verify settings.py reads DATABASE_* environment variables into DATABASES['default']."""
    monkeypatch.setenv("USE_SQLITE_TEST", "False")
    monkeypatch.setenv("DATABASE_NAME", "test_custom_db")
    monkeypatch.setenv("DATABASE_USER", "test_custom_user")
    monkeypatch.setenv("DATABASE_PASSWORD", "test_custom_pw")
    monkeypatch.setenv("DATABASE_HOST", "custom_host")
    monkeypatch.setenv("DATABASE_PORT", "9999")

    from dicoevent import settings

    importlib.reload(settings)

    db_conf = settings.DATABASES["default"]
    assert db_conf["ENGINE"] == "django.db.backends.postgresql"
    assert db_conf["NAME"] == "test_custom_db"
    assert db_conf["USER"] == "test_custom_user"
    assert db_conf["PASSWORD"] == "test_custom_pw"
    assert db_conf["HOST"] == "custom_host"
    assert db_conf["PORT"] == "9999"

    # Reset
    monkeypatch.setenv("USE_SQLITE_TEST", "True")
    importlib.reload(settings)


def test_settings_reads_backing_services_env_vars(monkeypatch):
    """Verify settings.py reads MinIO, Redis, Celery, and SMTP settings from env."""
    monkeypatch.setenv("MINIO_ENDPOINT_URL", "minio.example.com:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minio_test_key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minio_test_secret")
    monkeypatch.setenv("REDIS_HOST", "redis.example.com")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://redis.example.com:6379/5")
    monkeypatch.setenv("MAIL_HOST", "smtp.example.com")
    monkeypatch.setenv("MAIL_PORT", "2525")
    monkeypatch.setenv("MAIL_USER", "smtp_user")
    monkeypatch.setenv("MAIL_PASSWORD", "smtp_pass")

    from dicoevent import settings

    importlib.reload(settings)

    assert settings.MINIO_ENDPOINT_URL == "minio.example.com:9000"
    assert settings.MINIO_ACCESS_KEY == "minio_test_key"
    assert settings.MINIO_SECRET_KEY == "minio_test_secret"
    assert settings.REDIS_HOST == "redis.example.com"
    assert settings.CELERY_BROKER_URL == "redis://redis.example.com:6379/5"
    assert settings.MAIL_HOST == "smtp.example.com"
    assert settings.MAIL_PORT == "2525"
    assert settings.MAIL_USER == "smtp_user"
    assert settings.MAIL_PASSWORD == "smtp_pass"
    assert settings.EMAIL_HOST == "smtp.example.com"
    assert settings.EMAIL_PORT == 2525


def test_settings_redis_cache_configuration(monkeypatch):
    """Verify settings.py defines REDIS_HOST, REDIS_PORT, CACHE_TTL=3600, and CACHES default TIMEOUT=3600."""
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("USE_SQLITE_TEST", "False")

    from dicoevent import settings

    importlib.reload(settings)

    assert settings.REDIS_HOST == "localhost"
    assert settings.REDIS_PORT == "6379"
    assert getattr(settings, "CACHE_TTL", None) == 3600
    assert settings.CACHES["default"]["TIMEOUT"] == 3600

    assert settings.CACHES["default"]["BACKEND"] == "django_redis.cache.RedisCache"
    assert settings.CACHES["default"]["LOCATION"] == "redis://localhost:6379/1"

    # Reset
    monkeypatch.setenv("USE_SQLITE_TEST", "True")
    importlib.reload(settings)
    assert settings.CACHES["default"]["TIMEOUT"] == 3600


def test_core_and_users_apps_configured():
    """Verify core, users, events, and tickets applications are installed and configured with canonical labels."""
    from django.apps import apps
    from django.conf import settings

    assert "apps.core" in settings.INSTALLED_APPS or "apps.core.apps.CoreConfig" in settings.INSTALLED_APPS
    assert "apps.users" in settings.INSTALLED_APPS or "apps.users.apps.UsersConfig" in settings.INSTALLED_APPS
    assert "apps.events" in settings.INSTALLED_APPS or "apps.events.apps.EventsConfig" in settings.INSTALLED_APPS
    assert "apps.tickets" in settings.INSTALLED_APPS or "apps.tickets.apps.TicketsConfig" in settings.INSTALLED_APPS
    assert apps.get_app_config("core").label == "core"
    assert apps.get_app_config("users").label == "users"
    assert apps.get_app_config("events").label == "events"
    assert apps.get_app_config("tickets").label == "tickets"
    assert settings.AUTH_USER_MODEL == "users.User"
    assert settings.REST_FRAMEWORK.get("EXCEPTION_HANDLER") == "apps.core.exceptions.custom_exception_handler"
