import os
import importlib
import pytest

def test_settings_reads_database_env_vars(monkeypatch):
    """Verify settings.py reads DATABASE_* environment variables into DATABASES['default']."""
    monkeypatch.setenv('USE_SQLITE_TEST', 'False')
    monkeypatch.setenv('DATABASE_NAME', 'test_custom_db')
    monkeypatch.setenv('DATABASE_USER', 'test_custom_user')
    monkeypatch.setenv('DATABASE_PASSWORD', 'test_custom_pw')
    monkeypatch.setenv('DATABASE_HOST', 'custom_host')
    monkeypatch.setenv('DATABASE_PORT', '9999')

    from dicoevent import settings
    importlib.reload(settings)

    db_conf = settings.DATABASES['default']
    assert db_conf['ENGINE'] == 'django.db.backends.postgresql'
    assert db_conf['NAME'] == 'test_custom_db'
    assert db_conf['USER'] == 'test_custom_user'
    assert db_conf['PASSWORD'] == 'test_custom_pw'
    assert db_conf['HOST'] == 'custom_host'
    assert db_conf['PORT'] == '9999'

    # Reset
    monkeypatch.setenv('USE_SQLITE_TEST', 'True')
    importlib.reload(settings)

def test_settings_reads_backing_services_env_vars(monkeypatch):
    """Verify settings.py reads MinIO, Redis, Celery, and SMTP settings from env."""
    monkeypatch.setenv('MINIO_ENDPOINT_URL', 'minio.example.com:9000')
    monkeypatch.setenv('MINIO_ACCESS_KEY', 'minio_test_key')
    monkeypatch.setenv('MINIO_SECRET_KEY', 'minio_test_secret')
    monkeypatch.setenv('REDIS_HOST', 'redis.example.com')
    monkeypatch.setenv('CELERY_BROKER_URL', 'redis://redis.example.com:6379/5')
    monkeypatch.setenv('MAIL_HOST', 'smtp.example.com')
    monkeypatch.setenv('MAIL_PORT', '2525')
    monkeypatch.setenv('MAIL_USER', 'smtp_user')
    monkeypatch.setenv('MAIL_PASSWORD', 'smtp_pass')

    from dicoevent import settings
    importlib.reload(settings)

    assert settings.MINIO_ENDPOINT_URL == 'minio.example.com:9000'
    assert settings.MINIO_ACCESS_KEY == 'minio_test_key'
    assert settings.MINIO_SECRET_KEY == 'minio_test_secret'
    assert settings.REDIS_HOST == 'redis.example.com'
    assert settings.CELERY_BROKER_URL == 'redis://redis.example.com:6379/5'
    assert settings.MAIL_HOST == 'smtp.example.com'
    assert settings.MAIL_PORT == '2525'
    assert settings.MAIL_USER == 'smtp_user'
    assert settings.MAIL_PASSWORD == 'smtp_pass'
    assert settings.EMAIL_HOST == 'smtp.example.com'
    assert settings.EMAIL_PORT == 2525
