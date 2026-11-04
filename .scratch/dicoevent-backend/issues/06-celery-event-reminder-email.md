# 06: Celery Asynchronous H-2 Hour Event Reminder Email

**What to build:** Configure Celery and Django SMTP email delivery so that creating a Registration (`POST /api/registrations/`) schedules an asynchronous reminder email task for 2 hours prior to the Event's `start_time` (with immediate asynchronous execution when the test Event's `start_time - 2h` is already in the past).

**Blocked by:** 03: Tickets, Registrations, Payments & V1 ERD

**Status:** resolved

- [x] Celery broker URL is read from the `CELERY_BROKER_URL` environment variable.
- [x] Django email SMTP configuration is read from `MAIL_HOST`, `MAIL_PORT`, `MAIL_USER`, and `MAIL_PASSWORD` environment variables.
- [x] Creating a Registration via `POST /api/registrations/` calculates `eta = event.start_time - timedelta(hours=2)`.
- [x] When `eta` is in the future relative to the current time, the reminder email Celery task is scheduled via `apply_async` with `eta=eta`; when `eta` is in the past or present (such as Postman's historical test dates), the task is dispatched immediately via `.delay()`.
- [x] Executing the Celery reminder task sends an email reminder containing the Event details to the registered User's `email` address and logs an `INFO` entry via Loguru to `application.log` (or an `ERROR` entry to `error.log` on failure).
- [x] Automated tests verify both the H-2 hour `eta` scheduling calculation for future Events and end-to-end email delivery to `django.core.mail.outbox` when a Registration is created.
