from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from loguru import logger

from api.models import Registration


@shared_task
def send_event_reminder_email(registration_id: str):
    """
    Celery task to send an event reminder email to a registered user.
    """
    if not registration_id:
        logger.error("Cannot send reminder email: No registration_id provided.")
        return

    try:
        registration = Registration.objects.select_related("ticket__event", "user").get(id=registration_id)
    except Registration.DoesNotExist:
        logger.error(f"Cannot send reminder email: Registration {registration_id} not found.")
        return

    user_email = registration.user.email
    if not user_email:
        logger.error(f"Cannot send reminder email: No recipient email provided for registration {registration_id}.")
        return

    event = registration.event
    event_name = event.name
    start_time = event.start_time
    location = event.location

    subject = f"Event Reminder: {event_name}"
    message = (
        f"Hi,\n\n"
        f"This is a reminder for your upcoming event.\n\n"
        f"Event Details:\n"
        f"- Name: {event_name}\n"
        f"- Location: {location}\n"
        f"- Start Time: {start_time}\n\n"
        f"We look forward to seeing you there!\n"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@dicoevent.com")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info(
            f"Event reminder email sent successfully to '{user_email}' for event '{event_name}' "
            f"(Registration ID: {registration_id})"
        )
    except Exception as e:
        logger.error(
            f"Failed to send event reminder email to '{user_email}' for event '{event_name}' "
            f"(Registration ID: {registration_id}): {str(e)}"
        )
        raise


def schedule_event_reminder(registration):
    """
    Calculates eta = event.start_time - 2 hours.
    If eta > now, schedules reminder via Celery apply_async(eta=eta).
    If eta <= now, dispatches immediately via Celery delay().
    Gracefully catches broker connection errors to ensure registration creation does not fail.
    """
    event = registration.event
    event_start = event.start_time
    if timezone.is_naive(event_start):
        event_start = timezone.make_aware(event_start)

    eta = event_start - timedelta(hours=2)
    now = timezone.now()
    reg_id_str = str(registration.id)

    try:
        if eta > now:
            send_event_reminder_email.apply_async(args=[reg_id_str], eta=eta)
            logger.info(f"Event reminder scheduled for {eta} (Registration ID: {reg_id_str}, Event: '{event.name}')")
        else:
            send_event_reminder_email.delay(reg_id_str)
            logger.info(f"Event reminder dispatched immediately (Registration ID: {reg_id_str}, Event: '{event.name}')")
    except Exception as e:
        logger.error(f"Broker connection error scheduling event reminder for registration {reg_id_str}: {e}")
