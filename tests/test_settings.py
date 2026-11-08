import importlib

import pytest


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
    """Verify all domain apps are installed with canonical labels and legacy api app is completely removed."""
    import os

    from django.apps import apps
    from django.conf import settings

    assert "apps.core" in settings.INSTALLED_APPS or "apps.core.apps.CoreConfig" in settings.INSTALLED_APPS
    assert "apps.users" in settings.INSTALLED_APPS or "apps.users.apps.UsersConfig" in settings.INSTALLED_APPS
    assert "apps.events" in settings.INSTALLED_APPS or "apps.events.apps.EventsConfig" in settings.INSTALLED_APPS
    assert "apps.tickets" in settings.INSTALLED_APPS or "apps.tickets.apps.TicketsConfig" in settings.INSTALLED_APPS
    assert (
        "apps.registrations" in settings.INSTALLED_APPS
        or "apps.registrations.apps.RegistrationsConfig" in settings.INSTALLED_APPS
    )
    assert "apps.payments" in settings.INSTALLED_APPS or "apps.payments.apps.PaymentsConfig" in settings.INSTALLED_APPS

    assert "api" not in settings.INSTALLED_APPS
    assert "api.apps.ApiConfig" not in settings.INSTALLED_APPS

    assert apps.get_app_config("core").label == "core"
    assert apps.get_app_config("users").label == "users"
    assert apps.get_app_config("events").label == "events"
    assert apps.get_app_config("tickets").label == "tickets"
    assert apps.get_app_config("registrations").label == "registrations"
    assert apps.get_app_config("payments").label == "payments"
    assert settings.AUTH_USER_MODEL == "users.User"
    assert settings.REST_FRAMEWORK.get("EXCEPTION_HANDLER") == "apps.core.exceptions.custom_exception_handler"

    # Verify api directory is completely removed
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_dir = os.path.join(root_dir, "api")
    assert not os.path.exists(api_dir), f"Legacy monolith directory still exists at {api_dir}"


def test_dependencies_contain_django_cors_headers():
    """Verify django-cors-headers is listed in Pipfile and requirements.txt."""
    from pathlib import Path

    root_dir = Path(__file__).resolve().parent.parent
    pipfile_content = (root_dir / "Pipfile").read_text(encoding="utf-8").lower()
    requirements_content = (root_dir / "requirements.txt").read_text(encoding="utf-8").lower()

    assert "django-cors-headers" in pipfile_content, "django-cors-headers must be in Pipfile"
    assert "django-cors-headers" in requirements_content, "django-cors-headers must be in requirements.txt"


def test_settings_package_modules_exist_and_base_dir_resolves_to_root(monkeypatch):
    """Verify settings package has base, dev, prod, and test modules, all with BASE_DIR at repo root."""
    from pathlib import Path

    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("SECRET_KEY", "valid-prod-secret-key-for-test-resolution")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.dicoevent.com")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.dicoevent.com")

    expected_root = Path(__file__).resolve().parent.parent

    for mod_name in [
        "dicoevent.settings.base",
        "dicoevent.settings.dev",
        "dicoevent.settings.prod",
        "dicoevent.settings.test",
    ]:
        mod = importlib.import_module(mod_name)
        assert hasattr(mod, "BASE_DIR"), f"{mod_name} must define BASE_DIR"
        assert Path(mod.BASE_DIR).resolve() == expected_root.resolve(), (
            f"{mod_name}.BASE_DIR resolves to {Path(mod.BASE_DIR).resolve()}, expected {expected_root.resolve()}"
        )


def test_cors_installed_and_middleware_ordering():
    """Verify 'corsheaders' is in INSTALLED_APPS and CorsMiddleware is placed at index 2 (after WhiteNoise)."""
    from django.conf import settings

    assert "corsheaders" in settings.INSTALLED_APPS, "'corsheaders' must be in INSTALLED_APPS"

    middleware = list(settings.MIDDLEWARE)
    security_middleware = "django.middleware.security.SecurityMiddleware"
    whitenoise_middleware = "whitenoise.middleware.WhiteNoiseMiddleware"
    cors_middleware = "corsheaders.middleware.CorsMiddleware"
    session_middleware = "django.contrib.sessions.middleware.SessionMiddleware"

    assert security_middleware in middleware
    assert whitenoise_middleware in middleware
    assert cors_middleware in middleware
    assert session_middleware in middleware

    whitenoise_index = middleware.index(whitenoise_middleware)
    cors_index = middleware.index(cors_middleware)
    session_index = middleware.index(session_middleware)

    assert cors_index == whitenoise_index + 1, "CorsMiddleware must be immediately after WhiteNoiseMiddleware"
    assert session_index == cors_index + 1, "SessionMiddleware must be immediately after CorsMiddleware"


def test_prod_settings_fail_fast(monkeypatch):
    """Verify prod settings forces DEBUG=False and raises ImproperlyConfigured for missing/insecure settings."""
    from django.core.exceptions import ImproperlyConfigured

    # 1. DEBUG=True raises ImproperlyConfigured
    monkeypatch.setenv("DEBUG", "True")
    monkeypatch.setenv("SECRET_KEY", "prod-secret-key-12345-very-secure")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.dicoevent.com")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.dicoevent.com")
    with pytest.raises(ImproperlyConfigured, match="DEBUG must be False"):
        if "dicoevent.settings.prod" in importlib.sys.modules:
            importlib.reload(importlib.sys.modules["dicoevent.settings.prod"])
        else:
            importlib.import_module("dicoevent.settings.prod")

    # 2. Insecure / empty SECRET_KEY raises ImproperlyConfigured
    monkeypatch.setenv("DEBUG", "False")
    for bad_key in [
        "",
        "   ",
        "django-insecure-default-key-for-dev",
        "django-insecure-dicoevent-default-secret-key-change-in-production",
    ]:
        monkeypatch.setenv("SECRET_KEY", bad_key)
        with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
            if "dicoevent.settings.prod" in importlib.sys.modules:
                importlib.reload(importlib.sys.modules["dicoevent.settings.prod"])
            else:
                importlib.import_module("dicoevent.settings.prod")

    # 3. Empty or wildcard ALLOWED_HOSTS raises ImproperlyConfigured
    monkeypatch.setenv("SECRET_KEY", "prod-secret-key-12345-very-secure")
    for bad_hosts in ["", "   ", "*", "api.dicoevent.com,*"]:
        monkeypatch.setenv("ALLOWED_HOSTS", bad_hosts)
        with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
            if "dicoevent.settings.prod" in importlib.sys.modules:
                importlib.reload(importlib.sys.modules["dicoevent.settings.prod"])
            else:
                importlib.import_module("dicoevent.settings.prod")

    # 4. Wildcard in CORS_ALLOWED_ORIGINS raises ImproperlyConfigured
    monkeypatch.setenv("ALLOWED_HOSTS", "api.dicoevent.com")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ImproperlyConfigured, match="CORS_ALLOWED_ORIGINS"):
        if "dicoevent.settings.prod" in importlib.sys.modules:
            importlib.reload(importlib.sys.modules["dicoevent.settings.prod"])
        else:
            importlib.import_module("dicoevent.settings.prod")

    # 5. Valid prod configuration succeeds and enforces security headers by default
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.dicoevent.com")
    monkeypatch.delenv("SECURE_SSL_REDIRECT", raising=False)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("CSRF_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("SECURE_HSTS_SECONDS", raising=False)
    monkeypatch.delenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", raising=False)
    monkeypatch.delenv("SECURE_HSTS_PRELOAD", raising=False)

    if "dicoevent.settings.prod" in importlib.sys.modules:
        prod_mod = importlib.reload(importlib.sys.modules["dicoevent.settings.prod"])
    else:
        prod_mod = importlib.import_module("dicoevent.settings.prod")

    assert prod_mod.DEBUG is False
    assert prod_mod.SECURE_SSL_REDIRECT is True
    assert prod_mod.SESSION_COOKIE_SECURE is True
    assert prod_mod.CSRF_COOKIE_SECURE is True
    assert prod_mod.SECURE_HSTS_SECONDS == 31536000
    assert prod_mod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert prod_mod.SECURE_HSTS_PRELOAD is True
    assert prod_mod.CORS_ALLOW_ALL_ORIGINS is False
    assert prod_mod.ENABLE_SILK is False


def test_test_settings_configuration(monkeypatch):
    """Verify test settings defaults: MD5 hasher, eager Celery, Silk disabled, and SQLite/Postgres switching."""

    monkeypatch.setenv("USE_SQLITE_TEST", "True")
    if "dicoevent.settings.test" in importlib.sys.modules:
        test_mod = importlib.reload(importlib.sys.modules["dicoevent.settings.test"])
    else:
        test_mod = importlib.import_module("dicoevent.settings.test")

    assert test_mod.ENABLE_SILK is False
    assert "silk.middleware.SilkyMiddleware" not in test_mod.MIDDLEWARE
    assert test_mod.PASSWORD_HASHERS == ["django.contrib.auth.hashers.MD5PasswordHasher"]
    assert test_mod.CELERY_TASK_ALWAYS_EAGER is True
    assert test_mod.CELERY_TASK_EAGER_PROPAGATES is True
    assert test_mod.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert test_mod.DATABASES["default"]["NAME"] == ":memory:"
    assert test_mod.CACHES["default"]["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache"
    assert "http://localhost:3000" in test_mod.CORS_ALLOWED_ORIGINS

    # Switch to Postgres/Redis
    monkeypatch.setenv("USE_SQLITE_TEST", "False")
    test_mod = importlib.reload(test_mod)
    assert test_mod.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert test_mod.CACHES["default"]["BACKEND"] == "django_redis.cache.RedisCache"

    # Reset
    monkeypatch.setenv("USE_SQLITE_TEST", "True")
    importlib.reload(test_mod)


def test_dev_settings_defaults(monkeypatch):
    """Verify dev settings defaults: DEBUG=True, default ALLOWED_HOSTS, ENABLE_SILK=True, local CORS."""

    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("ENABLE_SILK", raising=False)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    if "dicoevent.settings.dev" in importlib.sys.modules:
        dev_mod = importlib.reload(importlib.sys.modules["dicoevent.settings.dev"])
    else:
        dev_mod = importlib.import_module("dicoevent.settings.dev")

    assert dev_mod.DEBUG is True
    assert "localhost" in dev_mod.ALLOWED_HOSTS
    assert "127.0.0.1" in dev_mod.ALLOWED_HOSTS
    assert dev_mod.ENABLE_SILK is True
    assert "silk.middleware.SilkyMiddleware" in dev_mod.MIDDLEWARE
    assert dev_mod.CORS_ALLOW_ALL_ORIGINS is False
    assert "http://localhost:3000" in dev_mod.CORS_ALLOWED_ORIGINS
    assert "http://localhost:5173" in dev_mod.CORS_ALLOWED_ORIGINS


def test_dynamic_env_package_routing(monkeypatch):
    """Verify dicoevent.settings dynamically routes via DJANGO_ENV."""
    from dicoevent import settings as root_settings

    # 1. Dev routing
    monkeypatch.setenv("DJANGO_ENV", "dev")
    importlib.reload(root_settings)
    assert root_settings.DEBUG is True
    assert root_settings.ENABLE_SILK is True

    # 2. Test routing
    monkeypatch.setenv("DJANGO_ENV", "test")
    monkeypatch.setenv("USE_SQLITE_TEST", "True")
    importlib.reload(root_settings)
    assert root_settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert root_settings.CELERY_TASK_ALWAYS_EAGER is True

    # 3. Prod routing (with valid env)
    monkeypatch.setenv("DJANGO_ENV", "prod")
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("SECRET_KEY", "prod-secret-key-12345-very-secure")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.dicoevent.com")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.dicoevent.com")
    importlib.reload(root_settings)
    assert root_settings.DEBUG is False
    assert root_settings.SECURE_HSTS_SECONDS == 31536000

    # Reset
    monkeypatch.setenv("DJANGO_ENV", "test")
    importlib.reload(root_settings)


@pytest.mark.django_db
def test_cors_allowed_and_disallowed_origins_http_headers(api_client):
    """
    Verify CORS middleware sets Access-Control-Allow-Origin for whitelisted origins
    and omits it for disallowed origins.
    """
    from rest_framework import status

    # Whitelisted origin
    response_allowed = api_client.get("/api/events/", HTTP_ORIGIN="http://localhost:3000")
    assert response_allowed.status_code == status.HTTP_200_OK
    assert response_allowed.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"

    # Disallowed origin
    response_disallowed = api_client.get("/api/events/", HTTP_ORIGIN="http://malicious-site.com")
    assert response_disallowed.status_code == status.HTTP_200_OK
    assert "Access-Control-Allow-Origin" not in response_disallowed.headers

    # Preflight OPTIONS request from whitelisted origin
    response_preflight = api_client.options(
        "/api/events/",
        HTTP_ORIGIN="http://localhost:3000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )
    assert response_preflight.status_code == status.HTTP_200_OK
    assert response_preflight.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert "GET" in response_preflight.headers.get("Access-Control-Allow-Methods", "")
