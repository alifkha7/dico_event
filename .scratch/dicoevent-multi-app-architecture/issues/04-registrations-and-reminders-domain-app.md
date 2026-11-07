# 04: Deepened Registrations & Reminder Lifecycle Application (`registrations`)

**What to build:** Extract **Registration** management and asynchronous 2-hour pre-**Event** reminder notifications (`send_event_reminder_email` and `schedule_event_reminder`) into a dedicated `registrations` Django application (`db_table = "registrations"`), folding resilient reminder scheduling directly into the **Registration** creation lifecycle (`RegistrationSerializer.create`) so that creating a **Registration** from any caller automatically enforces the 2-hour reminder invariant without inline task orchestration in the HTTP view.

**Blocked by:** 03: Tickets Domain Application (`tickets`)

**Status:** resolved

- [x] The `registrations` application is registered in Django's installed applications under the `registrations` label and owns the **Registration** model (`db_table = "registrations"`, cascading delete from **Ticket** and **User**) and its initial migration.
- [x] `RegistrationSerializer` inherits from `DualKeyModelSerializer` to resolve `ticket` / `ticket_id` (with `select_related("event")`) and `user` / `user_id`, and its `create` lifecycle automatically invokes `schedule_event_reminder(registration)` inside a resilient error boundary.
- [x] The `registrations` tasks module exports `send_event_reminder_email` and `schedule_event_reminder` (computing `eta = event.start_time - 2 hours` or executing immediately when within the 2-hour window), discovered automatically by Celery.
- [x] `RegistrationViewSet` configures `select_related("ticket", "ticket__event", "user")`, uses `PartialUpdateMixin` and the declarative permission policy (**Admin**/**Superuser** full access, **User** ownership on mutations, and ADR-0001 unauthenticated detail `retrieve`), and contains no inline task scheduling imports.
- [x] The **Registration** and Celery reminder test suites are updated to import from the `registrations` application, and the entire test suite and `ruff` checks pass.
