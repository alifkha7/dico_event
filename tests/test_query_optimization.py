from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status

from apps.events.models import Event
from apps.payments.models import Payment
from apps.registrations.models import Registration
from apps.tickets.models import Ticket

User = get_user_model()


# ==========================================
# 1. Database Model Indexing Tests
# ==========================================


def test_event_model_database_indexes():
    """Verify Event model defines database indexes on start_time, status, and category."""
    index_fields = [tuple(idx.fields) for idx in Event._meta.indexes]
    assert ("start_time",) in index_fields, "Event._meta.indexes missing index on ('start_time',)"
    assert ("status",) in index_fields, "Event._meta.indexes missing index on ('status',)"
    assert ("category",) in index_fields, "Event._meta.indexes missing index on ('category',)"


# ==========================================
# 2. O(1) Constant Query Count Tests (2 vs 10 records)
# ==========================================


@pytest.mark.django_db
def test_users_list_num_queries_constant(api_client, superuser, get_auth_header, django_assert_num_queries):
    """
    Verify GET /api/users/ executes the exact same constant number of SQL queries
    regardless of whether there are 2 or 10 user records (O(1) query count, no N+1).
    """
    headers = get_auth_header(superuser)

    # 1. Seed 2 users
    User.objects.create_user(username="query_user_1", email="query1@dicoevent.com", password="password123")
    User.objects.create_user(username="query_user_2", email="query2@dicoevent.com", password="password123")

    with CaptureQueriesContext(connection) as ctx_2:
        res_2 = api_client.get("/api/users/", **headers)
    assert res_2.status_code == status.HTTP_200_OK
    queries_2 = len(ctx_2.captured_queries)

    # 2. Seed 8 more users (total 10+ users)
    for i in range(3, 11):
        User.objects.create_user(username=f"query_user_{i}", email=f"query{i}@dicoevent.com", password="password123")

    with django_assert_num_queries(queries_2):
        res_10 = api_client.get("/api/users/", **headers)
    assert res_10.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_events_list_num_queries_constant(api_client, organizer_user, django_assert_num_queries):
    """
    Verify GET /api/events/ executes constant number of SQL queries for 2 vs 10 events
    when cache is cleared prior to each request (O(1) query count, no N+1).
    """
    now = datetime.now(timezone.utc)

    # 1. Seed 2 events
    for i in range(1, 3):
        Event.objects.create(
            name=f"Query Event {i}",
            description="Test description",
            location="Online",
            start_time=now + timedelta(days=i),
            end_time=now + timedelta(days=i, hours=2),
            status="published",
            quota=100,
            category="Tech",
            organizer=organizer_user,
        )

    cache.clear()
    with CaptureQueriesContext(connection) as ctx_2:
        res_2 = api_client.get("/api/events/")
    assert res_2.status_code == status.HTTP_200_OK
    queries_2 = len(ctx_2.captured_queries)

    # 2. Seed 8 more events (10 total)
    for i in range(3, 11):
        Event.objects.create(
            name=f"Query Event {i}",
            description="Test description",
            location="Online",
            start_time=now + timedelta(days=i),
            end_time=now + timedelta(days=i, hours=2),
            status="published",
            quota=100,
            category="Tech",
            organizer=organizer_user,
        )

    cache.clear()
    with django_assert_num_queries(queries_2):
        res_10 = api_client.get("/api/events/")
    assert res_10.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_tickets_list_num_queries_constant(api_client, organizer_user, django_assert_num_queries):
    """
    Verify GET /api/tickets/ executes constant number of SQL queries for 2 vs 10 tickets
    (O(1) query count, no N+1 on event or organizer).
    """
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Ticket Query Event",
        description="Event for tickets",
        location="Online",
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status="published",
        quota=200,
        category="Business",
        organizer=organizer_user,
    )

    # 1. Seed 2 tickets
    for i in range(1, 3):
        Ticket.objects.create(
            event=event,
            name=f"Ticket {i}",
            price=10000 * i,
            sales_start=now - timedelta(days=1),
            sales_end=now + timedelta(days=4),
            quota=50,
        )

    with CaptureQueriesContext(connection) as ctx_2:
        res_2 = api_client.get("/api/tickets/")
    assert res_2.status_code == status.HTTP_200_OK
    queries_2 = len(ctx_2.captured_queries)

    # 2. Seed 8 more tickets (10 total)
    for i in range(3, 11):
        Ticket.objects.create(
            event=event,
            name=f"Ticket {i}",
            price=10000 * i,
            sales_start=now - timedelta(days=1),
            sales_end=now + timedelta(days=4),
            quota=50,
        )

    with django_assert_num_queries(queries_2):
        res_10 = api_client.get("/api/tickets/")
    assert res_10.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_registrations_list_num_queries_constant(
    api_client, superuser, organizer_user, get_auth_header, django_assert_num_queries
):
    """
    Verify GET /api/registrations/ executes constant number of SQL queries for 2 vs 10 registrations
    (O(1) query count, no N+1 on ticket, event, or user).
    """
    headers = get_auth_header(superuser)
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Registration Query Event",
        description="Event for registrations",
        location="Online",
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status="published",
        quota=200,
        category="Business",
        organizer=organizer_user,
    )
    ticket = Ticket.objects.create(
        event=event,
        name="General Admission",
        price=10000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=4),
        quota=100,
    )

    # 1. Seed 2 registrations
    users = []
    for i in range(1, 11):
        u = User.objects.create_user(username=f"reg_user_{i}", email=f"reg{i}@dicoevent.com", password="password123")
        users.append(u)

    Registration.objects.create(ticket=ticket, user=users[0])
    Registration.objects.create(ticket=ticket, user=users[1])

    with CaptureQueriesContext(connection) as ctx_2:
        res_2 = api_client.get("/api/registrations/", **headers)
    assert res_2.status_code == status.HTTP_200_OK
    queries_2 = len(ctx_2.captured_queries)

    # 2. Seed 8 more registrations (10 total)
    for i in range(2, 10):
        Registration.objects.create(ticket=ticket, user=users[i])

    with django_assert_num_queries(queries_2):
        res_10 = api_client.get("/api/registrations/", **headers)
    assert res_10.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_payments_list_num_queries_constant(
    api_client, superuser, organizer_user, get_auth_header, django_assert_num_queries
):
    """
    Verify GET /api/payments/ executes constant number of SQL queries for 2 vs 10 payments
    (O(1) query count, no N+1 on registration or registrant user).
    """
    headers = get_auth_header(superuser)
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Payment Query Event",
        description="Event for payments",
        location="Online",
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status="published",
        quota=200,
        category="Business",
        organizer=organizer_user,
    )
    ticket = Ticket.objects.create(
        event=event,
        name="VIP Ticket",
        price=50000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=4),
        quota=100,
    )

    registrations = []
    for i in range(1, 11):
        u = User.objects.create_user(username=f"pay_user_{i}", email=f"pay{i}@dicoevent.com", password="password123")
        reg = Registration.objects.create(ticket=ticket, user=u)
        registrations.append(reg)

    # 1. Seed 2 payments
    Payment.objects.create(
        registration=registrations[0], payment_method="Bank Transfer", payment_status="Completed", amount_paid=50000
    )
    Payment.objects.create(
        registration=registrations[1], payment_method="Credit Card", payment_status="Completed", amount_paid=50000
    )

    with CaptureQueriesContext(connection) as ctx_2:
        res_2 = api_client.get("/api/payments/", **headers)
    assert res_2.status_code == status.HTTP_200_OK
    queries_2 = len(ctx_2.captured_queries)

    # 2. Seed 8 more payments (10 total)
    for i in range(2, 10):
        Payment.objects.create(
            registration=registrations[i], payment_method="E-Wallet", payment_status="Completed", amount_paid=50000
        )

    with django_assert_num_queries(queries_2):
        res_10 = api_client.get("/api/payments/", **headers)
    assert res_10.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_scoped_registrations_list_num_queries_constant_for_organizer(
    api_client, organizer_user, get_auth_header, django_assert_num_queries
):
    """
    Verify GET /api/registrations/ by an Organizer executes a constant number of SQL queries
    for 2 vs 10 registrations across owned events (O(1) query count under scoped queryset).
    """
    headers = get_auth_header(organizer_user)
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Org Scoped Reg Event",
        description="Event for scoped registrations",
        location="Online",
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status="published",
        quota=200,
        category="Tech",
        organizer=organizer_user,
    )
    ticket = Ticket.objects.create(
        event=event,
        name="General Admission",
        price=10000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=4),
        quota=100,
    )

    # 1. Seed 2 registrations
    users = [
        User.objects.create_user(
            username=f"scoped_reg_u_{i}", email=f"scoped_reg_{i}@dicoevent.com", password="password123"
        )
        for i in range(1, 11)
    ]
    Registration.objects.create(ticket=ticket, user=users[0])
    Registration.objects.create(ticket=ticket, user=users[1])

    with CaptureQueriesContext(connection) as ctx_2:
        res_2 = api_client.get("/api/registrations/", **headers)
    assert res_2.status_code == status.HTTP_200_OK
    queries_2 = len(ctx_2.captured_queries)

    # 2. Seed 8 more registrations (10 total)
    for i in range(2, 10):
        Registration.objects.create(ticket=ticket, user=users[i])

    with django_assert_num_queries(queries_2):
        res_10 = api_client.get("/api/registrations/", **headers)
    assert res_10.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_scoped_payments_list_num_queries_constant_for_organizer(
    api_client, organizer_user, get_auth_header, django_assert_num_queries
):
    """
    Verify GET /api/payments/ by an Organizer executes a constant number of SQL queries
    for 2 vs 10 payments across owned events (O(1) query count under scoped queryset).
    """
    headers = get_auth_header(organizer_user)
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Org Scoped Pay Event",
        description="Event for scoped payments",
        location="Online",
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status="published",
        quota=200,
        category="Tech",
        organizer=organizer_user,
    )
    ticket = Ticket.objects.create(
        event=event,
        name="General Admission",
        price=15000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=4),
        quota=100,
    )

    users = [
        User.objects.create_user(
            username=f"scoped_pay_u_{i}", email=f"scoped_pay_{i}@dicoevent.com", password="password123"
        )
        for i in range(1, 11)
    ]
    regs = [Registration.objects.create(ticket=ticket, user=u) for u in users]

    # 1. Seed 2 payments
    Payment.objects.create(
        registration=regs[0], payment_method="Bank Transfer", payment_status="Completed", amount_paid=15000
    )
    Payment.objects.create(
        registration=regs[1], payment_method="Credit Card", payment_status="Completed", amount_paid=15000
    )

    with CaptureQueriesContext(connection) as ctx_2:
        res_2 = api_client.get("/api/payments/", **headers)
    assert res_2.status_code == status.HTTP_200_OK
    queries_2 = len(ctx_2.captured_queries)

    # 2. Seed 8 more payments (10 total)
    for i in range(2, 10):
        Payment.objects.create(
            registration=regs[i], payment_method="GoPay", payment_status="Completed", amount_paid=15000
        )

    with django_assert_num_queries(queries_2):
        res_10 = api_client.get("/api/payments/", **headers)
    assert res_10.status_code == status.HTTP_200_OK


# ==========================================
# 3. Object-level Permission Check & Mutation Query Tests
# ==========================================


@pytest.mark.django_db
def test_ticket_update_object_permission_query_efficiency(api_client, organizer_user, get_auth_header):
    """
    Verify PUT /api/tickets/<id>/ by organizer efficiently checks event ownership
    without redundant SQL queries when TicketViewSet queryset uses select_related('event', 'event__organizer').
    """
    headers = get_auth_header(organizer_user)
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Organizer Event",
        description="Owned by organizer",
        location="Online",
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status="published",
        quota=100,
        category="Tech",
        organizer=organizer_user,
    )
    ticket = Ticket.objects.create(
        event=event,
        name="Early Bird",
        price=25000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=2),
        quota=50,
    )

    update_payload = {"name": "Early Bird Renamed", "price": 30000}
    with CaptureQueriesContext(connection) as ctx:
        res = api_client.put(f"/api/tickets/{ticket.id}/", update_payload, format="json", **headers)

    assert res.status_code == status.HTTP_200_OK
    # Ticket lookup should select_related event and event__organizer in the initial query
    event_selects = [
        q["sql"] for q in ctx.captured_queries if 'FROM "events"' in q["sql"] or "FROM `events`" in q["sql"]
    ]
    assert len(event_selects) == 0, f"Found separate queries for events table during ticket update: {event_selects}"


@pytest.mark.django_db
def test_payment_update_object_permission_query_efficiency(api_client, regular_user, organizer_user, get_auth_header):
    """
    Verify PUT /api/payments/<id>/ by owner user checks permission without separate queries
    to the registrations table when PaymentViewSet queryset uses select_related('registration', 'registration__user').
    """
    headers = get_auth_header(regular_user)
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Payment Perm Event",
        description="Event for payment perm test",
        location="Online",
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status="published",
        quota=100,
        category="Tech",
        organizer=organizer_user,
    )
    ticket = Ticket.objects.create(
        event=event,
        name="Standard",
        price=10000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=2),
        quota=50,
    )
    registration = Registration.objects.create(ticket=ticket, user=regular_user)
    payment = Payment.objects.create(
        registration=registration,
        payment_method="Bank Transfer",
        payment_status="Pending",
        amount_paid=10000,
    )

    update_payload = {"payment_status": "Completed"}
    with CaptureQueriesContext(connection) as ctx:
        res = api_client.put(f"/api/payments/{payment.id}/", update_payload, format="json", **headers)

    assert res.status_code == status.HTTP_200_OK
    registration_selects = [
        q["sql"]
        for q in ctx.captured_queries
        if ('FROM "registrations"' in q["sql"] or "FROM `registrations`" in q["sql"])
    ]
    assert len(registration_selects) == 0, (
        f"Found separate query to registrations table during payment update: {registration_selects}"
    )


@pytest.mark.django_db
def test_registration_creation_reminder_query_efficiency(api_client, regular_user, organizer_user, get_auth_header):
    """
    Verify POST /api/registrations/ loads Ticket.objects.select_related('event')
    so that schedule_event_reminder accessing registration.event does not trigger an extra query to events table.
    """
    headers = get_auth_header(regular_user)
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Reminder Query Event",
        description="Event for reminder query test",
        location="Online",
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status="published",
        quota=100,
        category="Tech",
        organizer=organizer_user,
    )
    ticket = Ticket.objects.create(
        event=event,
        name="Reminder Ticket",
        price=10000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=2),
        quota=50,
    )

    payload = {"ticket_id": str(ticket.id)}
    with (
        patch("apps.registrations.tasks.send_event_reminder_email.apply_async") as mock_apply_async,
        CaptureQueriesContext(connection) as ctx,
    ):
        res = api_client.post("/api/registrations/", payload, format="json", **headers)

    assert res.status_code == status.HTTP_201_CREATED
    assert mock_apply_async.called

    # Check queries: the ticket fetch in serializer should join events,
    # meaning no isolated "SELECT ... FROM events WHERE id = ..."
    event_separate_selects = [
        q["sql"]
        for q in ctx.captured_queries
        if ('FROM "events"' in q["sql"] or "FROM `events`" in q["sql"]) and "JOIN" not in q["sql"]
    ]
    assert len(event_separate_selects) == 0, (
        f"Detected separate query to events table in registration creation / reminder: {event_separate_selects}"
    )


# ==========================================
# 4. django-silk Configuration and ADR-0002 Integration Tests
# ==========================================


def test_django_silk_installed_and_configured():
    """Verify 'silk' is in INSTALLED_APPS and ENABLE_SILK conforms to ADR-0002."""
    assert "silk" in settings.INSTALLED_APPS, "'silk' must be present in INSTALLED_APPS"
    assert hasattr(settings, "ENABLE_SILK"), "settings must define ENABLE_SILK"
    # In pytest/test runs, ENABLE_SILK should default to False
    assert settings.ENABLE_SILK is False, "ENABLE_SILK should default to False when running tests"
    # SilkyMiddleware should not be in MIDDLEWARE during tests
    assert "silk.middleware.SilkyMiddleware" not in settings.MIDDLEWARE, (
        "silk.middleware.SilkyMiddleware should not be active in settings.MIDDLEWARE when ENABLE_SILK is False"
    )


@pytest.mark.django_db
def test_django_silk_route_accessible(api_client, superuser, get_auth_header):
    """
    Verify /silk/ URL route is conditionally enabled: returns 404 when ENABLE_SILK is False,
    and returns 200 OK when ENABLE_SILK is True.
    """
    import importlib

    from django.test import override_settings
    from django.urls import clear_url_caches

    import dicoevent.urls

    headers = get_auth_header(superuser)

    # 1. By default in tests, ENABLE_SILK is False -> /silk/ route is not registered (404)
    response_disabled = api_client.get("/silk/", **headers)
    assert response_disabled.status_code == status.HTTP_404_NOT_FOUND

    # 2. When ENABLE_SILK is True, reload urls and clear cache -> /silk/ route is accessible (200 OK)
    with override_settings(ENABLE_SILK=True):
        importlib.reload(dicoevent.urls)
        clear_url_caches()
        try:
            response = api_client.get("/silk/", **headers)
            assert response.status_code == status.HTTP_200_OK, (
                f"Expected /silk/ to return 200 OK, got {response.status_code}"
            )
        finally:
            importlib.reload(dicoevent.urls)
            clear_url_caches()
