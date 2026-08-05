# ruff: noqa: E501
from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from loguru import logger

from registrations.models import Registration


@shared_task
def send_ticket_email(user_email, username, registration_id):
    subject = "Reminder: Acara Anda Akan Segera Dimulai"

    # Plain text version (fallback for email clients that don't support HTML)
    text_content = f"""Halo {username},

    Terima kasih telah memesan tiket di Dicoding Event!

    Berikut adalah detail pemesanan tiket Anda:

    ID Pemesanan: {registration_id}

    Acara Anda akan dimulai dalam 2 jam! Pastikan Anda sudah bersiap-siap dan datang ke venue tepat waktu.

    Kami tunggu kedatangan Anda di Venue!

    Terima kasih,
    Tim Dicoding Event

    Pesan ini dikirim secara otomatis. Mohon tidak membalas pesan ini.
    """

    # HTML formatted version
    html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #E50914; text-align: center;">Reminder Acara Anda</h2>
                <p>Halo <strong>{username}</strong>,</p>
                <p>Terima kasih telah memesan tiket di <strong>Dicoding Event</strong>!</p>
                <p><strong>Detail Pemesanan Tiket Anda:</strong></p>
                <p style="background-color: #f8f8f8; padding: 10px; border-radius: 5px;">
                    <strong>ID Pemesanan:</strong> {registration_id}
                </p>
                <p>Acara Anda akan <strong>dimulai dalam 2 jam</strong>! Pastikan Anda sudah bersiap-siap dan datang ke venue tepat waktu.</p>
                <p>Kami tunggu kedatangan Anda di Venue</p>
                <br>
                <p style="font-size: 12px; color: #777; text-align: center;">
                    Pesan ini dikirim secara otomatis. Mohon tidak membalas pesan ini.
                </p>
                <p style="font-size: 12px; color: #777; text-align: center;">
                    <strong>Dicoding Event Team</strong>
                </p>
            </div>
        </body>
        </html>
        """

    email = EmailMultiAlternatives(subject, text_content, "no-reply@eventticket.com", [user_email])
    email.attach_alternative(html_content, "text/html")
    email.send()
    return f"Email sent to {user_email}"


@shared_task
def check_and_send_reminders():
    now = timezone.now()
    two_hours_later = now + timedelta(hours=2)
    two_hours_and_15_mins_later = now + timedelta(hours=2, minutes=15)

    # Temukan pendaftaran untuk acara yang akan dimulai dalam rentang 2 jam hingga 2 jam 15 menit
    registrations = Registration.objects.filter(
        is_reminder_sent=False,
        ticket__event__start_time__gte=two_hours_later,
        ticket__event__start_time__lt=two_hours_and_15_mins_later,
    )

    count = 0
    for reg in registrations:
        send_ticket_email.delay(reg.user.email, reg.user.username, reg.id)
        reg.is_reminder_sent = True
        reg.save()
        count += 1
        logger.info(f"Queued reminder email for {reg.user.email} (Registration ID: {reg.id})")

    return f"Processed {count} reminders."
