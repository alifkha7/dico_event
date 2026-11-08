from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.events.models import Event
from apps.payments.models import Payment
from apps.registrations.models import Registration
from apps.tickets.models import Ticket

User = get_user_model()


@pytest.mark.django_db
def test_cascading_delete_ticket_to_registration_and_payment_adr_0001(
    api_client, superuser, organizer_user, regular_user, get_auth_header
):
    """
    Test ADR-0001 Requirement 4:
    In the Version 2 Postman collection, the [Mandatory] Payments -> Delete Payments step
    sends DELETE /api/tickets/{{ticketId}}/ and then asserts that
    GET /api/payments/{{paymentId}} returns 404 Not Found.
    """
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Cascading Test Event",
        description="Testing cascades",
        location="Online",
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=2),
        status="published",
        quota=100,
        category="Testing",
        organizer=organizer_user,
    )

    ticket = Ticket.objects.create(
        event=event,
        name="Cascade Ticket",
        price=50000,
        sales_start=now,
        sales_end=now + timedelta(days=1),
        quota=50,
    )

    registration = Registration.objects.create(
        ticket=ticket,
        user=regular_user,
    )

    payment = Payment.objects.create(
        registration=registration,
        payment_method="Credit Card",
        payment_status="Pending",
        amount_paid=50000,
    )

    ticket_id = str(ticket.id)
    registration_id = str(registration.id)
    payment_id = str(payment.id)

    headers = get_auth_header(superuser)

    # Verify they exist
    assert api_client.get(f"/api/tickets/{ticket_id}/").status_code == status.HTTP_200_OK
    assert api_client.get(f"/api/registrations/{registration_id}/", **headers).status_code == status.HTTP_200_OK
    assert api_client.get(f"/api/payments/{payment_id}/", **headers).status_code == status.HTTP_200_OK

    # Superuser deletes the Ticket
    del_res = api_client.delete(f"/api/tickets/{ticket_id}/", **headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # Verify ticket returns 404 with and without trailing slash
    assert api_client.get(f"/api/tickets/{ticket_id}/").status_code == status.HTTP_404_NOT_FOUND
    assert api_client.get(f"/api/tickets/{ticket_id}").status_code == status.HTTP_404_NOT_FOUND

    # Verify registration returns 404 with and without trailing slash
    assert api_client.get(f"/api/registrations/{registration_id}/", **headers).status_code == status.HTTP_404_NOT_FOUND
    assert api_client.get(f"/api/registrations/{registration_id}", **headers).status_code == status.HTTP_404_NOT_FOUND

    # Verify payment returns 404 with and without trailing slash per ADR-0001
    assert api_client.get(f"/api/payments/{payment_id}/", **headers).status_code == status.HTTP_404_NOT_FOUND
    assert api_client.get(f"/api/payments/{payment_id}", **headers).status_code == status.HTTP_404_NOT_FOUND

    # Verify DB rows are actually gone
    assert not Ticket.objects.filter(id=ticket.id).exists()
    assert not Registration.objects.filter(id=registration.id).exists()
    assert not Payment.objects.filter(id=payment.id).exists()
