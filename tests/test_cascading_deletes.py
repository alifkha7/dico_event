from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.events.models import Event
from apps.payments.models import Payment
from apps.registrations.models import Registration
from apps.tickets.models import Ticket

User = get_user_model()

PROTECTED_DETAIL = "Cannot delete this resource because it is referenced by existing transactional records."


@pytest.fixture
def test_setup_data(organizer_user, regular_user):
    """Fixture providing an event, ticket, registration, and payment hierarchy."""
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Audit Protection Summit",
        description="Testing relational audit protection",
        location="Hybrid",
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=2),
        status="published",
        quota=100,
        category="Conference",
        organizer=organizer_user,
    )

    ticket = Ticket.objects.create(
        event=event,
        name="General Admission",
        price=50000,
        sales_start=now - timedelta(hours=1),
        sales_end=now + timedelta(days=1),
        quota=50,
    )

    registration = Registration.objects.create(
        ticket=ticket,
        user=regular_user,
    )

    payment = Payment.objects.create(
        registration=registration,
        payment_method="Bank Transfer",
        payment_status="Pending",
        amount_paid=50000,
    )

    return {
        "event": event,
        "ticket": ticket,
        "registration": registration,
        "payment": payment,
        "organizer": organizer_user,
        "participant": regular_user,
    }


@pytest.mark.django_db
def test_delete_event_with_tickets_returns_409_conflict(api_client, superuser, get_auth_header, test_setup_data):
    """Verify attempting to DELETE an Event that has Tickets returns 409 Conflict and preserves records."""
    event = test_setup_data["event"]
    ticket = test_setup_data["ticket"]
    headers = get_auth_header(superuser)

    response = api_client.delete(f"/api/events/{event.id}/", **headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data == {"detail": PROTECTED_DETAIL}
    assert Event.objects.filter(id=event.id).exists()
    assert Ticket.objects.filter(id=ticket.id).exists()


@pytest.mark.django_db
def test_delete_ticket_with_registrations_returns_409_conflict(api_client, superuser, get_auth_header, test_setup_data):
    """Verify attempting to DELETE a Ticket that has Registrations returns 409 Conflict and preserves records."""
    ticket = test_setup_data["ticket"]
    registration = test_setup_data["registration"]
    headers = get_auth_header(superuser)

    response = api_client.delete(f"/api/tickets/{ticket.id}/", **headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data == {"detail": PROTECTED_DETAIL}
    assert Ticket.objects.filter(id=ticket.id).exists()
    assert Registration.objects.filter(id=registration.id).exists()


@pytest.mark.django_db
def test_delete_registration_with_payments_returns_409_conflict(
    api_client, regular_user, get_auth_header, test_setup_data
):
    """Verify attempting to DELETE a Registration that has Payments returns 409 Conflict and preserves records."""
    registration = test_setup_data["registration"]
    payment = test_setup_data["payment"]
    headers = get_auth_header(regular_user)

    response = api_client.delete(f"/api/registrations/{registration.id}/", **headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data == {"detail": PROTECTED_DETAIL}
    assert Registration.objects.filter(id=registration.id).exists()
    assert Payment.objects.filter(id=payment.id).exists()


@pytest.mark.django_db
def test_delete_user_with_registrations_returns_409_conflict(api_client, superuser, get_auth_header, test_setup_data):
    """Verify attempting to DELETE a User with Registrations returns 409 Conflict and preserves records."""
    participant = test_setup_data["participant"]
    registration = test_setup_data["registration"]
    headers = get_auth_header(superuser)

    response = api_client.delete(f"/api/users/{participant.id}/", **headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data == {"detail": PROTECTED_DETAIL}
    assert User.objects.filter(id=participant.id).exists()
    assert Registration.objects.filter(id=registration.id).exists()


@pytest.mark.django_db
def test_delete_user_with_owned_events_returns_409_conflict(api_client, superuser, get_auth_header, test_setup_data):
    """Verify attempting to DELETE an Organizer User with owned Events returns 409 Conflict and preserves records."""
    organizer = test_setup_data["organizer"]
    event = test_setup_data["event"]
    headers = get_auth_header(superuser)

    response = api_client.delete(f"/api/users/{organizer.id}/", **headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data == {"detail": PROTECTED_DETAIL}
    assert User.objects.filter(id=organizer.id).exists()
    assert Event.objects.filter(id=event.id).exists()


@pytest.mark.django_db
def test_clean_deletions_when_unreferenced_return_204_no_content(
    api_client, superuser, organizer_user, regular_user, get_auth_header
):
    """Verify deleting unreferenced Event, Ticket, Registration, and User succeeds with 204 No Content."""
    now = datetime.now(timezone.utc)
    headers = get_auth_header(superuser)

    # 1. Unreferenced Registration (no payments)
    solo_event = Event.objects.create(
        name="Solo Event",
        description="Desc",
        location="Online",
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=2),
        status="published",
        quota=50,
        category="Solo",
        organizer=organizer_user,
    )
    solo_ticket = Ticket.objects.create(
        event=solo_event,
        name="Solo Ticket",
        price=10000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=1),
        quota=20,
    )
    solo_reg = Registration.objects.create(ticket=solo_ticket, user=regular_user)
    res_reg = api_client.delete(f"/api/registrations/{solo_reg.id}/", **headers)
    assert res_reg.status_code == status.HTTP_204_NO_CONTENT
    assert not Registration.objects.filter(id=solo_reg.id).exists()

    # 2. Unreferenced Ticket (no registrations)
    res_ticket = api_client.delete(f"/api/tickets/{solo_ticket.id}/", **headers)
    assert res_ticket.status_code == status.HTTP_204_NO_CONTENT
    assert not Ticket.objects.filter(id=solo_ticket.id).exists()

    # 3. Unreferenced Event (no tickets)
    res_event = api_client.delete(f"/api/events/{solo_event.id}/", **headers)
    assert res_event.status_code == status.HTTP_204_NO_CONTENT
    assert not Event.objects.filter(id=solo_event.id).exists()

    # 4. Unreferenced User (no registrations, no owned events)
    clean_user = User.objects.create_user(
        username="clean_user",
        email="clean@example.com",
        password="ValidPassword123!",
    )
    res_user = api_client.delete(f"/api/users/{clean_user.id}/", **headers)
    assert res_user.status_code == status.HTTP_204_NO_CONTENT
    assert not User.objects.filter(id=clean_user.id).exists()
