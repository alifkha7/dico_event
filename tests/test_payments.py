import uuid
from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from api.models import Event, Payment, Registration, Ticket

User = get_user_model()


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
        sales_start=now,
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
def test_list_payments_regular_user_forbidden(api_client, regular_user, get_auth_header, sample_payment):
    """Verify standard User cannot list payments (403 Forbidden)."""
    headers = get_auth_header(regular_user)
    response = api_client.get("/api/payments/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_payments_unauthenticated(api_client, sample_payment):
    """Verify unauthenticated user cannot list payments (401 Unauthorized)."""
    response = api_client.get("/api/payments/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==========================================
# 3. Payment Retrieval (GET /api/payments/<id>/)
# ==========================================


@pytest.mark.django_db
def test_retrieve_payment_allow_any(api_client, sample_payment):
    """Verify unauthenticated GET /api/payments/<id>/ returns 200 OK per ADR-0001."""
    response = api_client.get(f"/api/payments/{sample_payment.id}/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(sample_payment.id)
    assert response.data["registration"] == str(sample_payment.registration_id)
    assert response.data["registration_id"] == str(sample_payment.registration_id)
    assert response.data["payment_method"] == sample_payment.payment_method
    assert response.data["payment_status"] == sample_payment.payment_status
    assert response.data["amount_paid"] == sample_payment.amount_paid


@pytest.mark.django_db
def test_retrieve_payment_no_trailing_slash(api_client, sample_payment):
    """Verify unauthenticated GET /api/payments/<id> works without trailing slash per ADR-0001."""
    response = api_client.get(f"/api/payments/{sample_payment.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(sample_payment.id)


@pytest.mark.django_db
def test_retrieve_payment_not_found(api_client):
    """Verify GET /api/payments/<nonexistent_id>/ returns 404 Not Found."""
    random_id = uuid.uuid4()
    response = api_client.get(f"/api/payments/{random_id}/")
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
    get_res = api_client.get(f"/api/payments/{payment_id}/")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_delete_payment_non_owner_forbidden(api_client, another_regular_user, get_auth_header, sample_payment):
    """Verify non-owner User cannot delete payment (403 Forbidden)."""
    headers = get_auth_header(another_regular_user)
    response = api_client.delete(f"/api/payments/{sample_payment.id}/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
