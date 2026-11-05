from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core import mail
from loguru import logger
from rest_framework import status

from api.models import Event, Registration, Ticket


@pytest.fixture
def future_event(organizer_user):
    now = datetime.now(timezone.utc)
    return Event.objects.create(
        name="Future AI Summit 2026",
        description="AI Summit in future",
        location="Jakarta Convention Center",
        start_time=now + timedelta(hours=6),
        end_time=now + timedelta(hours=10),
        status="published",
        quota=100,
        category="Technology",
        organizer=organizer_user,
    )


@pytest.fixture
def future_ticket(future_event):
    now = datetime.now(timezone.utc)
    return Ticket.objects.create(
        event=future_event,
        name="Early Bird",
        price=50000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(hours=5),
        quota=50,
    )


@pytest.fixture
def imminent_event(organizer_user):
    now = datetime.now(timezone.utc)
    # Event starting in 1 hour means start_time - 2h is 1 hour in the past
    return Event.objects.create(
        name="Imminent Workshop 2026",
        description="Workshop starting soon",
        location="Bandung Digital Valley",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=3),
        status="published",
        quota=50,
        category="Workshop",
        organizer=organizer_user,
    )


@pytest.fixture
def imminent_ticket(imminent_event):
    now = datetime.now(timezone.utc)
    return Ticket.objects.create(
        event=imminent_event,
        name="Standard Pass",
        price=75000,
        sales_start=now - timedelta(days=2),
        sales_end=now + timedelta(minutes=30),
        quota=50,
    )


@pytest.fixture
def historical_event(organizer_user):
    # Historical date like Postman test suite
    past_time = datetime(2024, 6, 21, 14, 0, 0, tzinfo=timezone.utc)
    return Event.objects.create(
        name="Postman Historical Event 2024",
        description="Historical event for compatibility tests",
        location="Online",
        start_time=past_time,
        end_time=past_time + timedelta(hours=2),
        status="published",
        quota=100,
        category="Archive",
        organizer=organizer_user,
    )


@pytest.fixture
def historical_ticket(historical_event):
    past_time = datetime(2024, 6, 21, 14, 0, 0, tzinfo=timezone.utc)
    return Ticket.objects.create(
        event=historical_event,
        name="Archive Ticket",
        price=0,
        sales_start=past_time - timedelta(days=7),
        sales_end=past_time,
        quota=100,
    )


# ==========================================
# 1. Settings Configuration Tests
# ==========================================


def test_celery_and_email_settings_from_env(monkeypatch):
    """Verify settings.py reads CELERY_BROKER_URL and MAIL_* environment variables."""
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://custom-redis:6379/3")
    monkeypatch.setenv("MAIL_HOST", "custom-smtp.example.com")
    monkeypatch.setenv("MAIL_PORT", "587")
    monkeypatch.setenv("MAIL_USER", "custom_user@example.com")
    monkeypatch.setenv("MAIL_PASSWORD", "custom_pass_123")

    import importlib

    from dicoevent import settings as dico_settings

    importlib.reload(dico_settings)

    assert dico_settings.CELERY_BROKER_URL == "redis://custom-redis:6379/3"
    assert dico_settings.MAIL_HOST == "custom-smtp.example.com"
    assert dico_settings.MAIL_PORT == "587"
    assert dico_settings.MAIL_USER == "custom_user@example.com"
    assert dico_settings.MAIL_PASSWORD == "custom_pass_123"
    assert dico_settings.EMAIL_HOST == "custom-smtp.example.com"
    assert dico_settings.EMAIL_PORT == 587
    assert dico_settings.EMAIL_HOST_USER == "custom_user@example.com"
    assert dico_settings.EMAIL_HOST_PASSWORD == "custom_pass_123"
    assert dico_settings.DEFAULT_FROM_EMAIL == "custom_user@example.com"
    assert dico_settings.CELERY_TASK_ALWAYS_EAGER is True
    assert dico_settings.CELERY_TASK_EAGER_PROPAGATES is True

    # Reset
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("MAIL_HOST", raising=False)
    monkeypatch.delenv("MAIL_PORT", raising=False)
    monkeypatch.delenv("MAIL_USER", raising=False)
    monkeypatch.delenv("MAIL_PASSWORD", raising=False)
    importlib.reload(dico_settings)


# ==========================================
# 2. Celery Task Execution & Logging Tests
# ==========================================


@pytest.mark.django_db
def test_send_event_reminder_email_task_success(future_ticket, regular_user):
    """Verify send_event_reminder_email delivers email with event details and logs INFO."""
    from api.tasks import send_event_reminder_email

    registration = Registration.objects.create(ticket=future_ticket, user=regular_user)
    event = future_ticket.event

    mail.outbox.clear()
    send_event_reminder_email(str(registration.id))

    # Verify email delivery
    assert len(mail.outbox) == 1
    sent_mail = mail.outbox[0]
    assert regular_user.email in sent_mail.to
    assert event.name in sent_mail.subject
    assert event.name in sent_mail.body
    assert event.location in sent_mail.body

    # Flush and verify Loguru application.log
    logger.complete()
    app_log = settings.BASE_DIR / "application.log"
    assert app_log.exists()
    content = app_log.read_text(encoding="utf-8")
    assert "INFO" in content
    assert event.name in content


@pytest.mark.django_db
def test_send_event_reminder_email_task_failure_logs_error(future_ticket, regular_user, monkeypatch):
    """Verify send_event_reminder_email logs ERROR to error.log and raises on exception."""
    from api.tasks import send_event_reminder_email

    registration = Registration.objects.create(ticket=future_ticket, user=regular_user)

    def mock_send_mail(*args, **kwargs):
        raise RuntimeError("Simulated SMTP network failure")

    monkeypatch.setattr("api.tasks.send_mail", mock_send_mail)

    with pytest.raises(RuntimeError, match="Simulated SMTP network failure"):
        send_event_reminder_email(str(registration.id))

    # Flush and verify Loguru error.log
    logger.complete()
    error_log = settings.BASE_DIR / "error.log"
    assert error_log.exists()
    error_content = error_log.read_text(encoding="utf-8")
    assert "ERROR" in error_content
    assert "Simulated SMTP network failure" in error_content


# ==========================================
# 3. Reminder Scheduling Calculation Tests
# ==========================================


@pytest.mark.django_db
def test_schedule_event_reminder_future_event(future_ticket, regular_user):
    """Verify event starting in future schedules task with apply_async and eta = start_time - 2h."""
    from api.tasks import schedule_event_reminder, send_event_reminder_email

    registration = Registration.objects.create(ticket=future_ticket, user=regular_user)
    event = future_ticket.event
    expected_eta = event.start_time - timedelta(hours=2)

    with (
        patch.object(send_event_reminder_email, "apply_async") as mock_apply_async,
        patch.object(send_event_reminder_email, "delay") as mock_delay,
    ):
        schedule_event_reminder(registration)

        assert mock_apply_async.called
        assert not mock_delay.called
        call_kwargs = mock_apply_async.call_args.kwargs
        assert call_kwargs.get("eta") == expected_eta
        assert mock_apply_async.call_args[1]["args"] == [str(registration.id)] or mock_apply_async.call_args.kwargs[
            "args"
        ] == [str(registration.id)]


@pytest.mark.django_db
def test_schedule_event_reminder_imminent_event(imminent_ticket, regular_user):
    """Verify event whose start_time - 2h is in the past dispatches immediately via delay()."""
    from api.tasks import schedule_event_reminder, send_event_reminder_email

    registration = Registration.objects.create(ticket=imminent_ticket, user=regular_user)

    with (
        patch.object(send_event_reminder_email, "apply_async") as mock_apply_async,
        patch.object(send_event_reminder_email, "delay") as mock_delay,
    ):
        schedule_event_reminder(registration)

        assert mock_delay.called
        assert not mock_apply_async.called
        assert mock_delay.call_args[0] == (str(registration.id),)


@pytest.mark.django_db
def test_schedule_event_reminder_historical_event(historical_ticket, regular_user):
    """Verify historical event (e.g. Postman test date) dispatches immediately via delay()."""
    from api.tasks import schedule_event_reminder, send_event_reminder_email

    registration = Registration.objects.create(ticket=historical_ticket, user=regular_user)

    with (
        patch.object(send_event_reminder_email, "apply_async") as mock_apply_async,
        patch.object(send_event_reminder_email, "delay") as mock_delay,
    ):
        schedule_event_reminder(registration)

        assert mock_delay.called
        assert not mock_apply_async.called
        assert mock_delay.call_args[0] == (str(registration.id),)


@pytest.mark.django_db
def test_schedule_event_reminder_catches_broker_exception(future_ticket, regular_user):
    """Verify broker connection errors are caught gracefully and do not propagate."""
    from api.tasks import schedule_event_reminder, send_event_reminder_email

    registration = Registration.objects.create(ticket=future_ticket, user=regular_user)

    with patch.object(send_event_reminder_email, "apply_async", side_effect=Exception("Redis broker unreachable")):
        # Must not raise
        schedule_event_reminder(registration)

    logger.complete()
    error_log = settings.BASE_DIR / "error.log"
    assert error_log.exists()
    assert "Redis broker unreachable" in error_log.read_text(encoding="utf-8")


# ==========================================
# 4. End-to-End Registration Creation API Tests
# ==========================================


@pytest.mark.django_db
def test_create_registration_api_schedules_future_reminder(api_client, regular_user, get_auth_header, future_ticket):
    """Verify POST /api/registrations/ calculates eta and schedules reminder."""
    from api.tasks import send_event_reminder_email

    headers = get_auth_header(regular_user)
    payload = {"ticket": str(future_ticket.id)}

    with (
        patch.object(send_event_reminder_email, "apply_async") as mock_apply_async,
        patch.object(send_event_reminder_email, "delay") as mock_delay,
    ):
        response = api_client.post("/api/registrations/", payload, format="json", **headers)

        assert response.status_code == status.HTTP_201_CREATED
        assert mock_apply_async.called
        assert not mock_delay.called
        expected_eta = future_ticket.event.start_time - timedelta(hours=2)
        assert mock_apply_async.call_args.kwargs["eta"] == expected_eta
        assert mock_apply_async.call_args.kwargs["args"] == [response.data["id"]]


@pytest.mark.django_db
def test_create_registration_api_dispatches_imminent_reminder(
    api_client, regular_user, get_auth_header, imminent_ticket
):
    """Verify POST /api/registrations/ calls delay() for imminent event (start_time - 2h < now)."""
    from api.tasks import send_event_reminder_email

    headers = get_auth_header(regular_user)
    payload = {"ticket": str(imminent_ticket.id)}

    with (
        patch.object(send_event_reminder_email, "apply_async") as mock_apply_async,
        patch.object(send_event_reminder_email, "delay") as mock_delay,
    ):
        response = api_client.post("/api/registrations/", payload, format="json", **headers)

        assert response.status_code == status.HTTP_201_CREATED
        assert mock_delay.called
        assert not mock_apply_async.called
        assert mock_delay.call_args[0] == (response.data["id"],)


@pytest.mark.django_db
def test_create_registration_api_delivers_email_eagerly(api_client, regular_user, get_auth_header, imminent_ticket):
    """Verify POST /api/registrations/ in eager mode sends email to django.core.mail.outbox."""
    headers = get_auth_header(regular_user)
    payload = {"ticket": str(imminent_ticket.id)}

    mail.outbox.clear()
    response = api_client.post("/api/registrations/", payload, format="json", **headers)

    assert response.status_code == status.HTTP_201_CREATED
    assert len(mail.outbox) == 1
    assert regular_user.email in mail.outbox[0].to
    assert imminent_ticket.event.name in mail.outbox[0].subject
