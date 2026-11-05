import pytest
from django.conf import settings
from loguru import logger


@pytest.mark.django_db
def test_loguru_application_and_error_logging(api_client, regular_user):
    """Verify INFO logs are recorded in application.log and ERROR logs in error.log."""
    app_log_path = settings.BASE_DIR / "application.log"
    error_log_path = settings.BASE_DIR / "error.log"

    # Trigger an INFO event (login)
    api_client.post(
        "/api/login/",
        {
            "username": regular_user.username,
            "password": "password123",
        },
        format="json",
    )

    # Trigger an ERROR event (failed login / bad request)
    api_client.post(
        "/api/login/",
        {
            "username": regular_user.username,
            "password": "wrongpassword",
        },
        format="json",
    )

    # Ensure log buffers are flushed
    logger.complete()

    assert app_log_path.exists(), "application.log should exist"
    assert error_log_path.exists(), "error.log should exist"

    app_content = app_log_path.read_text(encoding="utf-8")
    error_content = error_log_path.read_text(encoding="utf-8")

    assert "INFO" in app_content
    assert "logged in successfully" in app_content

    assert "ERROR" in error_content
    assert "Failed login" in error_content or "401" in error_content
