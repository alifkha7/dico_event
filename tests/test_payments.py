import uuid
from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.core.mixins import PartialUpdateMixin
from apps.core.permissions import RoleOwnershipPermission
from apps.core.serializers import DualKeyModelSerializer
from apps.events.models import Event
from apps.payments.models import Payment
from apps.payments.permissions import PaymentViewSetPermission
from apps.payments.serializers import PaymentSerializer
from apps.payments.views import PaymentViewSet
from apps.registrations.models import Registration
from apps.tickets.models import Ticket

User = get_user_model()


# ==========================================
# 0. Direct Imports and Domain Architectural Integrity
# ==========================================


def test_payments_app_direct_imports():
    """Verify Payment model, serializer, viewset, and permission are configured under apps.payments."""
    assert Payment._meta.app_label == "payments"
    assert Payment._meta.db_table == "payments"
    assert issubclass(PaymentSerializer, DualKeyModelSerializer)
    assert issubclass(PaymentViewSetPermission, RoleOwnershipPermission)
    assert issubclass(PaymentViewSet, PartialUpdateMixin)


@pytest.mark.django_db
def test_payment_model_user_property_shortcuts(sample_payment, regular_user):
    """Verify Payment model provides .user and .user_id property shortcuts to registration.user."""
    assert sample_payment.user == regular_user
    assert sample_payment.user_id == regular_user.id


@pytest.fixture
def sample_ticket(organizer_user):
    now = datetime.now(timezone.utc)
    event = Event.objects.create(
        name="Tech Conference 2026",
        description="Conference description",
        location="Jakarta",
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status="published",
        quota=200,
        category="Tech",
        organizer=organizer_user,
    )
    return Ticket.objects.create(
        event=event,
        name="General Admission",
        price=100000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=4),
        quota=100,
    )


@pytest.fixture
def sample_registration(sample_ticket, regular_user):
    return Registration.objects.create(
        ticket=sample_ticket,
        user=regular_user,
    )


@pytest.fixture
def sample_payment_data(sample_registration):
    return {
        "registration_id": str(sample_registration.id),
        "payment_method": "Credit Card",
        "payment_status": "pending",
        "amount_paid": 100000,
    }


@pytest.fixture
def sample_payment(sample_registration):
    return Payment.objects.create(
        registration=sample_registration,
        payment_method="Bank Transfer",
        payment_status="Pending",
        amount_paid=100000,
    )


@pytest.fixture
def another_regular_user(db):
    return User.objects.create_user(
        username="another_user",
        email="another@dicoevent.com",
        password="password123",
    )


# ==========================================
# 1. Payment Creation (POST /api/payments/)
# ==========================================


@pytest.mark.django_db
def test_create_payment_authenticated_user(api_client, regular_user, get_auth_header, sample_payment_data):
    """Verify authenticated user can create payment with registration_id."""
    headers = get_auth_header(regular_user)
    response = api_client.post("/api/payments/", sample_payment_data, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert "id" in response.data
    assert uuid.UUID(response.data["id"])
    assert response.data["registration"] == sample_payment_data["registration_id"]
    assert response.data["registration_id"] == sample_payment_data["registration_id"]
    assert response.data["payment_method"] == sample_payment_data["payment_method"]
    assert response.data["payment_status"] == sample_payment_data["payment_status"]
    assert response.data["amount_paid"] == 100000
    assert isinstance(response.data["amount_paid"], int)


@pytest.mark.django_db
def test_create_payment_accepts_registration_field_key(api_client, regular_user, get_auth_header, sample_registration):
    """Verify payment creation accepts 'registration' key instead of 'registration_id'."""
    headers = get_auth_header(regular_user)
    payload = {
        "registration": str(sample_registration.id),
        "payment_method": "GoPay",
        "payment_status": "pending",
        "amount_paid": 100000,
    }
    response = api_client.post("/api/payments/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["registration"] == str(sample_registration.id)
    assert response.data["registration_id"] == str(sample_registration.id)


@pytest.mark.django_db
def test_create_payment_no_trailing_slash(api_client, regular_user, get_auth_header, sample_payment_data):
    """Verify POST /api/payments without trailing slash works."""
    headers = get_auth_header(regular_user)
    response = api_client.post("/api/payments", sample_payment_data, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_create_payment_unauthenticated(api_client, sample_payment_data):
    """Verify unauthenticated user cannot create payment (401 Unauthorized)."""
    response = api_client.post("/api/payments/", sample_payment_data, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.parametrize("invalid_amount", [0, -100, -50000])
def test_create_payment_invalid_amount_paid_rejected(
    api_client, regular_user, get_auth_header, sample_payment_data, invalid_amount
):
    """Verify payment creation rejects non-positive amount_paid values (400 Bad Request)."""
    headers = get_auth_header(regular_user)
    payload = {**sample_payment_data, "amount_paid": invalid_amount}
    response = api_client.post("/api/payments/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "amount_paid" in response.data


@pytest.mark.django_db
def test_create_payment_other_user_registration_forbidden(
    api_client, another_regular_user, get_auth_header, sample_payment_data
):
    """Verify non-admin User cannot create payment for another User's registration (403 Forbidden)."""
    headers = get_auth_header(another_regular_user)
    response = api_client.post("/api/payments/", sample_payment_data, format="json", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# 2. Payment Listing (GET /api/payments/)
# ==========================================


@pytest.mark.django_db
def test_list_payments_superuser(api_client, superuser, get_auth_header, sample_payment):
    """Verify Superuser can list payments wrapped in {"payments": [...] }."""
    headers = get_auth_header(superuser)
    response = api_client.get("/api/payments/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "payments" in response.data
    assert any(p["id"] == str(sample_payment.id) for p in response.data["payments"])


@pytest.mark.django_db
def test_list_payments_admin(api_client, admin_user, get_auth_header, sample_payment):
    """Verify Admin can list payments."""
    headers = get_auth_header(admin_user)
    response = api_client.get("/api/payments/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "payments" in response.data


@pytest.mark.django_db
def test_list_payments_no_trailing_slash(api_client, admin_user, get_auth_header, sample_payment):
    """Verify GET /api/payments works without trailing slash."""
    headers = get_auth_header(admin_user)
    response = api_client.get("/api/payments", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "payments" in response.data


@pytest.mark.django_db
def test_list_payments_regular_user_scoped(
    api_client, regular_user, another_regular_user, sample_ticket, get_auth_header, sample_payment
):
    """Verify standard User can list payments and sees only their own payments (scoped 200 OK)."""
    # Create another user's registration and payment
    other_reg = Registration.objects.create(ticket=sample_ticket, user=another_regular_user)
    other_payment = Payment.objects.create(
        registration=other_reg,
        payment_method="GoPay",
        payment_status="Completed",
        amount_paid=100000,
    )

    headers = get_auth_header(regular_user)
    response = api_client.get("/api/payments/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "payments" in response.data
    pay_ids = [p["id"] for p in response.data["payments"]]
    assert str(sample_payment.id) in pay_ids
    assert str(other_payment.id) not in pay_ids


@pytest.mark.django_db
def test_list_payments_organizer_and_dual_role(
    api_client, organizer_user, another_regular_user, sample_ticket, get_auth_header, sample_payment
):
    """
    Verify Organizer lists payments for events they own, and when acting in dual roles
    (Organizer + User paying for another organizer's event), receives the union of both scopes.
    """
    from django.contrib.auth.models import Group

    # Create another organizer and their event/ticket/registration/payment
    organizer_group, _ = Group.objects.get_or_create(name="organizer")
    other_organizer = User.objects.create_user(
        username="other_org_pay", email="other_org_pay@dicoevent.com", password="password123"
    )
    other_organizer.groups.add(organizer_group)

    now = datetime.now(timezone.utc)
    other_event = Event.objects.create(
        name="Other Org Pay Event",
        description="Event by other organizer",
        location="Surabaya",
        start_time=now + timedelta(days=7),
        end_time=now + timedelta(days=8),
        status="published",
        quota=100,
        category="Tech",
        organizer=other_organizer,
    )
    other_ticket = Ticket.objects.create(
        event=other_event,
        name="Standard",
        price=50000,
        sales_start=now - timedelta(days=1),
        sales_end=now + timedelta(days=5),
        quota=50,
    )

    # 1. Payment for another organizer's event by another participant (should NOT be visible)
    other_participant_reg = Registration.objects.create(ticket=other_ticket, user=another_regular_user)
    other_participant_payment = Payment.objects.create(
        registration=other_participant_reg,
        payment_method="GoPay",
        payment_status="Completed",
        amount_paid=50000,
    )

    # 2. Payment for another organizer's event where organizer_user participates as a User
    organizer_personal_reg = Registration.objects.create(ticket=other_ticket, user=organizer_user)
    organizer_personal_payment = Payment.objects.create(
        registration=organizer_personal_reg,
        payment_method="Credit Card",
        payment_status="Completed",
        amount_paid=50000,
    )

    # Call GET /api/payments/ as organizer_user
    headers = get_auth_header(organizer_user)
    response = api_client.get("/api/payments/", **headers)
    assert response.status_code == status.HTTP_200_OK
    pay_ids = [p["id"] for p in response.data["payments"]]

    # Must see:
    # - sample_payment (attendee payment for organizer_user's event)
    # - organizer_personal_payment (organizer_user's personal payment)
    assert str(sample_payment.id) in pay_ids
    assert str(organizer_personal_payment.id) in pay_ids
    # Must NOT see:
    # - other_participant_payment (unrelated event participant)
    assert str(other_participant_payment.id) not in pay_ids


@pytest.mark.django_db
def test_list_payments_unauthenticated(api_client, sample_payment):
    """Verify unauthenticated user cannot list payments (401 Unauthorized)."""
    response = api_client.get("/api/payments/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==========================================
# 3. Payment Retrieval (GET /api/payments/<id>/)
# ==========================================


@pytest.mark.django_db
def test_retrieve_payment_unauthenticated_unauthorized(api_client, sample_payment):
    """Verify unauthenticated GET /api/payments/<id>/ returns 401 Unauthorized."""
    response = api_client.get(f"/api/payments/{sample_payment.id}/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_retrieve_payment_no_trailing_slash_unauthenticated(api_client, sample_payment):
    """Verify unauthenticated GET /api/payments/<id> returns 401 Unauthorized without trailing slash."""
    response = api_client.get(f"/api/payments/{sample_payment.id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_retrieve_payment_owner(api_client, regular_user, get_auth_header, sample_payment):
    """Verify owner User can retrieve their own payment (200 OK)."""
    headers = get_auth_header(regular_user)
    response = api_client.get(f"/api/payments/{sample_payment.id}/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(sample_payment.id)
    assert response.data["registration"] == str(sample_payment.registration_id)
    assert response.data["payment_status"] == sample_payment.payment_status


@pytest.mark.django_db
def test_retrieve_payment_other_user_forbidden(api_client, another_regular_user, get_auth_header, sample_payment):
    """Verify non-owner User cannot retrieve another user's payment (403 Forbidden)."""
    headers = get_auth_header(another_regular_user)
    response = api_client.get(f"/api/payments/{sample_payment.id}/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_retrieve_payment_organizer_owner(api_client, organizer_user, get_auth_header, sample_payment):
    """Verify Organizer can retrieve payment for an event they personally own (200 OK)."""
    headers = get_auth_header(organizer_user)
    response = api_client.get(f"/api/payments/{sample_payment.id}/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(sample_payment.id)


@pytest.mark.django_db
def test_retrieve_payment_other_organizer_forbidden(api_client, sample_payment, get_auth_header):
    """Verify an Organizer cannot retrieve a payment for an event owned by another Organizer (403 Forbidden)."""
    from django.contrib.auth.models import Group

    organizer_group, _ = Group.objects.get_or_create(name="organizer")
    other_organizer = User.objects.create_user(
        username="unrelated_org_pay", email="unrelated_org_pay@dicoevent.com", password="password123"
    )
    other_organizer.groups.add(organizer_group)

    headers = get_auth_header(other_organizer)
    response = api_client.get(f"/api/payments/{sample_payment.id}/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organizer_cannot_modify_or_delete_participant_payment(
    api_client, organizer_user, get_auth_header, sample_payment
):
    """Verify Organizer attempting to PUT/PATCH or DELETE a participant's payment receives 403 Forbidden."""
    headers = get_auth_header(organizer_user)

    # Attempt PUT
    put_res = api_client.put(
        f"/api/payments/{sample_payment.id}/",
        {"amount_paid": 100000},
        format="json",
        **headers,
    )
    assert put_res.status_code == status.HTTP_403_FORBIDDEN

    # Attempt PATCH
    patch_res = api_client.patch(
        f"/api/payments/{sample_payment.id}/",
        {"payment_method": "GoPay"},
        format="json",
        **headers,
    )
    assert patch_res.status_code == status.HTTP_403_FORBIDDEN

    # Attempt DELETE
    del_res = api_client.delete(f"/api/payments/{sample_payment.id}/", **headers)
    assert del_res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_retrieve_payment_not_found(api_client, superuser, get_auth_header):
    """Verify GET /api/payments/<nonexistent_id>/ returns 404 Not Found for authorized actor."""
    headers = get_auth_header(superuser)
    random_id = uuid.uuid4()
    response = api_client.get(f"/api/payments/{random_id}/", **headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ==========================================
# 4. Payment Update & Status Normalization (PUT /api/payments/<id>/)
# ==========================================


@pytest.mark.django_db
def test_update_payment_normalizes_completed_status(api_client, regular_user, get_auth_header, sample_payment):
    """Verify PUT /api/payments/<id>/ with 'completed' normalizes to 'Completed' per ADR-0001."""
    headers = get_auth_header(regular_user)
    payload = {"payment_status": "completed"}
    response = api_client.put(f"/api/payments/{sample_payment.id}/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["payment_status"] == "Completed"
    sample_payment.refresh_from_db()
    assert sample_payment.payment_status == "Completed"


@pytest.mark.django_db
def test_update_payment_admin(api_client, admin_user, get_auth_header, sample_payment):
    """Verify Admin can update any payment."""
    headers = get_auth_header(admin_user)
    payload = {"amount_paid": 120000}
    response = api_client.put(f"/api/payments/{sample_payment.id}/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_200_OK
    sample_payment.refresh_from_db()
    assert sample_payment.amount_paid == 120000


@pytest.mark.django_db
def test_update_payment_non_owner_forbidden(api_client, another_regular_user, get_auth_header, sample_payment):
    """Verify non-owner User cannot update payment (403 Forbidden)."""
    headers = get_auth_header(another_regular_user)
    payload = {"payment_status": "completed"}
    response = api_client.put(f"/api/payments/{sample_payment.id}/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_update_payment_reassign_to_other_user_registration_forbidden(
    api_client, regular_user, get_auth_header, sample_payment, sample_ticket, another_regular_user
):
    """Verify non-admin User cannot reassign payment to another User's registration (403 Forbidden)."""
    other_registration = Registration.objects.create(
        ticket=sample_ticket,
        user=another_regular_user,
    )
    headers = get_auth_header(regular_user)
    payload = {"registration_id": str(other_registration.id)}
    response = api_client.put(f"/api/payments/{sample_payment.id}/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# 5. Payment Deletion (DELETE /api/payments/<id>/)
# ==========================================


@pytest.mark.django_db
def test_delete_payment_owner_and_subsequent_404(api_client, regular_user, get_auth_header, sample_payment):
    """Verify owner User can delete payment and subsequent GET returns 404."""
    payment_id = sample_payment.id
    headers = get_auth_header(regular_user)
    response = api_client.delete(f"/api/payments/{payment_id}/", **headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Subsequent GET returns 404
    get_res = api_client.get(f"/api/payments/{payment_id}/", **headers)
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_delete_payment_non_owner_forbidden(api_client, another_regular_user, get_auth_header, sample_payment):
    """Verify non-owner User cannot delete payment (403 Forbidden)."""
    headers = get_auth_header(another_regular_user)
    response = api_client.delete(f"/api/payments/{sample_payment.id}/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
