import uuid
from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from apps.core.mixins import PartialUpdateMixin
from apps.core.permissions import RoleOwnershipPermission
from apps.core.serializers import DualKeyModelSerializer
from apps.events.models import Event
from apps.registrations.models import Registration
from apps.registrations.permissions import RegistrationViewSetPermission
from apps.registrations.serializers import RegistrationSerializer
from apps.registrations.views import RegistrationViewSet
from apps.tickets.models import Ticket

User = get_user_model()


# ==========================================
# 0. Direct Imports and Domain Architectural Integrity
# ==========================================


def test_registrations_app_direct_imports():
    """Verify Registration model, serializer, viewset, and permission are configured under apps.registrations."""
    assert Registration._meta.app_label == "registrations"
    assert Registration._meta.db_table == "registrations"
    assert issubclass(RegistrationSerializer, DualKeyModelSerializer)
    assert issubclass(RegistrationViewSetPermission, RoleOwnershipPermission)
    assert issubclass(RegistrationViewSet, PartialUpdateMixin)


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
def another_regular_user(db):
    return User.objects.create_user(
        username="another_user",
        email="another@dicoevent.com",
        password="password123",
    )


@pytest.fixture
def sample_registration(sample_ticket, regular_user):
    return Registration.objects.create(
        ticket=sample_ticket,
        user=regular_user,
    )


# ==========================================
# 1. Registration Creation (POST)
# ==========================================


@pytest.mark.django_db
def test_create_registration_authenticated_user(api_client, regular_user, get_auth_header, sample_ticket):
    """Verify authenticated user can create registration with ticket_id and user_id."""
    headers = get_auth_header(regular_user)
    payload = {
        "ticket_id": str(sample_ticket.id),
        "user_id": str(regular_user.id),
    }
    response = api_client.post("/api/registrations/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert "id" in response.data
    assert uuid.UUID(response.data["id"])
    assert response.data["ticket"] == str(sample_ticket.id)
    assert response.data["ticket_id"] == str(sample_ticket.id)
    assert response.data["user"] == str(regular_user.id)
    assert response.data["user_id"] == str(regular_user.id)


@pytest.mark.django_db
def test_create_registration_accepts_ticket_and_defaults_user(api_client, regular_user, get_auth_header, sample_ticket):
    """Verify registration accepts 'ticket' field and defaults user to request.user."""
    headers = get_auth_header(regular_user)
    payload = {
        "ticket": str(sample_ticket.id),
    }
    response = api_client.post("/api/registrations/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["ticket"] == str(sample_ticket.id)
    assert response.data["user"] == str(regular_user.id)


@pytest.mark.django_db
def test_create_registration_no_trailing_slash(api_client, regular_user, get_auth_header, sample_ticket):
    """Verify POST /api/registrations (without trailing slash) works per ADR-0001."""
    headers = get_auth_header(regular_user)
    payload = {
        "ticket_id": str(sample_ticket.id),
        "user_id": str(regular_user.id),
    }
    response = api_client.post("/api/registrations", payload, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_create_registration_unauthenticated(api_client, sample_ticket, regular_user):
    """Verify unauthenticated registration attempt returns 401 Unauthorized."""
    payload = {
        "ticket_id": str(sample_ticket.id),
        "user_id": str(regular_user.id),
    }
    response = api_client.post("/api/registrations/", payload, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==========================================
# 2. Registration Listing (GET /api/registrations/)
# ==========================================


@pytest.mark.django_db
def test_list_registrations_superuser(api_client, superuser, get_auth_header, sample_registration):
    """Verify Superuser can list registrations wrapped in {"registrations": [...] }."""
    headers = get_auth_header(superuser)
    response = api_client.get("/api/registrations/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "registrations" in response.data
    assert any(r["id"] == str(sample_registration.id) for r in response.data["registrations"])


@pytest.mark.django_db
def test_list_registrations_admin(api_client, admin_user, get_auth_header, sample_registration):
    """Verify Admin can list registrations."""
    headers = get_auth_header(admin_user)
    response = api_client.get("/api/registrations/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "registrations" in response.data


@pytest.mark.django_db
def test_list_registrations_no_trailing_slash(api_client, admin_user, get_auth_header, sample_registration):
    """Verify GET /api/registrations without trailing slash works."""
    headers = get_auth_header(admin_user)
    response = api_client.get("/api/registrations", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "registrations" in response.data


@pytest.mark.django_db
def test_list_registrations_regular_user_scoped(
    api_client, regular_user, another_regular_user, sample_ticket, get_auth_header, sample_registration
):
    """Verify standard User can list registrations and sees only their own registrations (scoped 200 OK)."""
    # Create another user's registration
    other_reg = Registration.objects.create(ticket=sample_ticket, user=another_regular_user)

    headers = get_auth_header(regular_user)
    response = api_client.get("/api/registrations/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "registrations" in response.data
    reg_ids = [r["id"] for r in response.data["registrations"]]
    assert str(sample_registration.id) in reg_ids
    assert str(other_reg.id) not in reg_ids


@pytest.mark.django_db
def test_list_registrations_organizer_and_dual_role(
    api_client, organizer_user, another_regular_user, sample_ticket, get_auth_header, sample_registration
):
    """
    Verify Organizer lists registrations for events they own, and when acting in dual roles
    (Organizer + User registered for another organizer's event), receives the union of both scopes.
    """
    from django.contrib.auth.models import Group

    # Create another organizer and their event/ticket
    organizer_group, _ = Group.objects.get_or_create(name="organizer")
    other_organizer = User.objects.create_user(
        username="other_org", email="other_org@dicoevent.com", password="password123"
    )
    other_organizer.groups.add(organizer_group)

    now = datetime.now(timezone.utc)
    other_event = Event.objects.create(
        name="Other Org Event",
        description="Event by other organizer",
        location="Bandung",
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
        sales_start=now,
        sales_end=now + timedelta(days=5),
        quota=50,
    )

    # 1. Registration for another organizer's event by another participant (should NOT be visible)
    other_participant_reg = Registration.objects.create(ticket=other_ticket, user=another_regular_user)

    # 2. Registration for another organizer's event where organizer_user participates as a User
    organizer_personal_reg = Registration.objects.create(ticket=other_ticket, user=organizer_user)

    # Call GET /api/registrations/ as organizer_user
    headers = get_auth_header(organizer_user)
    response = api_client.get("/api/registrations/", **headers)
    assert response.status_code == status.HTTP_200_OK
    reg_ids = [r["id"] for r in response.data["registrations"]]

    # Must see:
    # - sample_registration (attendee of organizer_user's event)
    # - organizer_personal_reg (organizer_user's personal participation)
    assert str(sample_registration.id) in reg_ids
    assert str(organizer_personal_reg.id) in reg_ids
    # Must NOT see:
    # - other_participant_reg (unrelated event participant)
    assert str(other_participant_reg.id) not in reg_ids


@pytest.mark.django_db
def test_list_registrations_unauthenticated(api_client, sample_registration):
    """Verify unauthenticated listing returns 401 Unauthorized."""
    response = api_client.get("/api/registrations/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==========================================
# 3. Registration Retrieval (GET /api/registrations/<id>/)
# ==========================================


@pytest.mark.django_db
def test_retrieve_registration_unauthenticated_unauthorized(api_client, sample_registration):
    """Verify unauthenticated GET /api/registrations/<id>/ returns 401 Unauthorized."""
    response = api_client.get(f"/api/registrations/{sample_registration.id}/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_retrieve_registration_no_trailing_slash_unauthenticated(api_client, sample_registration):
    """Verify unauthenticated GET /api/registrations/<id> returns 401 Unauthorized without trailing slash."""
    response = api_client.get(f"/api/registrations/{sample_registration.id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_retrieve_registration_owner(api_client, regular_user, get_auth_header, sample_registration):
    """Verify owning User can retrieve their own registration (200 OK)."""
    headers = get_auth_header(regular_user)
    response = api_client.get(f"/api/registrations/{sample_registration.id}/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(sample_registration.id)
    assert response.data["ticket"] == str(sample_registration.ticket_id)
    assert response.data["user"] == str(sample_registration.user_id)


@pytest.mark.django_db
def test_retrieve_registration_other_user_forbidden(
    api_client, another_regular_user, get_auth_header, sample_registration
):
    """Verify non-owner regular User cannot retrieve another user's registration (403 Forbidden)."""
    headers = get_auth_header(another_regular_user)
    response = api_client.get(f"/api/registrations/{sample_registration.id}/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_retrieve_registration_organizer_owner(api_client, organizer_user, get_auth_header, sample_registration):
    """Verify Organizer can retrieve registration for an event they personally own (200 OK)."""
    headers = get_auth_header(organizer_user)
    response = api_client.get(f"/api/registrations/{sample_registration.id}/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(sample_registration.id)


@pytest.mark.django_db
def test_retrieve_registration_other_organizer_forbidden(api_client, sample_registration, get_auth_header):
    """Verify an Organizer cannot retrieve a registration for an event owned by another Organizer (403 Forbidden)."""
    from django.contrib.auth.models import Group

    organizer_group, _ = Group.objects.get_or_create(name="organizer")
    other_organizer = User.objects.create_user(
        username="unrelated_org", email="unrelated_org@dicoevent.com", password="password123"
    )
    other_organizer.groups.add(organizer_group)

    headers = get_auth_header(other_organizer)
    response = api_client.get(f"/api/registrations/{sample_registration.id}/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_organizer_cannot_modify_or_delete_participant_registration(
    api_client, organizer_user, get_auth_header, sample_registration, sample_ticket
):
    """Verify Organizer attempting to PUT/PATCH or DELETE a participant's registration receives 403 Forbidden."""
    headers = get_auth_header(organizer_user)

    # Attempt PUT
    put_res = api_client.put(
        f"/api/registrations/{sample_registration.id}/",
        {"ticket_id": str(sample_ticket.id)},
        format="json",
        **headers,
    )
    assert put_res.status_code == status.HTTP_403_FORBIDDEN

    # Attempt PATCH
    patch_res = api_client.patch(
        f"/api/registrations/{sample_registration.id}/",
        {"ticket_id": str(sample_ticket.id)},
        format="json",
        **headers,
    )
    assert patch_res.status_code == status.HTTP_403_FORBIDDEN

    # Attempt DELETE
    del_res = api_client.delete(f"/api/registrations/{sample_registration.id}/", **headers)
    assert del_res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_retrieve_registration_not_found(api_client, superuser, get_auth_header):
    """Verify GET /api/registrations/<nonexistent_id>/ returns 404 Not Found for authorized actor."""
    headers = get_auth_header(superuser)
    random_id = uuid.uuid4()
    response = api_client.get(f"/api/registrations/{random_id}/", **headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ==========================================
# 4. Registration Update (PUT /api/registrations/<id>/)
# ==========================================


@pytest.mark.django_db
def test_update_registration_owner(api_client, regular_user, get_auth_header, sample_registration, sample_ticket):
    """Verify owner User can update their registration."""
    headers = get_auth_header(regular_user)
    response = api_client.put(
        f"/api/registrations/{sample_registration.id}/", {"ticket_id": str(sample_ticket.id)}, format="json", **headers
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_update_registration_admin(api_client, admin_user, get_auth_header, sample_registration, sample_ticket):
    """Verify Admin can update any registration."""
    headers = get_auth_header(admin_user)
    response = api_client.put(
        f"/api/registrations/{sample_registration.id}/", {"ticket_id": str(sample_ticket.id)}, format="json", **headers
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_update_registration_non_owner_forbidden(
    api_client, another_regular_user, get_auth_header, sample_registration, sample_ticket
):
    """Verify non-owner User cannot update registration (403 Forbidden)."""
    headers = get_auth_header(another_regular_user)
    response = api_client.put(
        f"/api/registrations/{sample_registration.id}/", {"ticket_id": str(sample_ticket.id)}, format="json", **headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# 5. Registration Deletion (DELETE /api/registrations/<id>/)
# ==========================================


@pytest.mark.django_db
def test_delete_registration_owner_and_subsequent_404(api_client, regular_user, get_auth_header, sample_registration):
    """Verify owner User can delete registration and subsequent GET returns 404."""
    reg_id = sample_registration.id
    headers = get_auth_header(regular_user)
    response = api_client.delete(f"/api/registrations/{reg_id}/", **headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Subsequent GET returns 404
    get_res = api_client.get(f"/api/registrations/{reg_id}/", **headers)
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_delete_registration_non_owner_forbidden(
    api_client, another_regular_user, get_auth_header, sample_registration
):
    """Verify non-owner User cannot delete registration (403 Forbidden)."""
    headers = get_auth_header(another_regular_user)
    response = api_client.delete(f"/api/registrations/{sample_registration.id}/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# 6. Deepened Seam and Ownership Validation Tests
# ==========================================


@pytest.mark.django_db
def test_create_registration_other_user_forbidden(
    api_client, regular_user, another_regular_user, get_auth_header, sample_ticket
):
    """Verify standard User cannot create a registration for another user (403 Forbidden)."""
    headers = get_auth_header(regular_user)
    payload = {
        "ticket_id": str(sample_ticket.id),
        "user_id": str(another_regular_user.id),
    }
    response = api_client.post("/api/registrations/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_create_registration_admin_for_other_user(api_client, admin_user, regular_user, get_auth_header, sample_ticket):
    """Verify Admin can create a registration for another user."""
    headers = get_auth_header(admin_user)
    payload = {
        "ticket_id": str(sample_ticket.id),
        "user_id": str(regular_user.id),
    }
    response = api_client.post("/api/registrations/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user"] == str(regular_user.id)


@pytest.mark.django_db
def test_update_registration_change_user_forbidden(
    api_client, regular_user, another_regular_user, get_auth_header, sample_registration
):
    """Verify standard User cannot reassign registration to another user (403 Forbidden)."""
    headers = get_auth_header(regular_user)
    response = api_client.put(
        f"/api/registrations/{sample_registration.id}/",
        {"user_id": str(another_regular_user.id)},
        format="json",
        **headers,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_registration_serializer_create_schedules_reminder(sample_ticket, regular_user):
    """Verify RegistrationSerializer.create automatically invokes schedule_event_reminder."""
    from unittest.mock import patch

    serializer = RegistrationSerializer(data={"ticket_id": str(sample_ticket.id), "user_id": str(regular_user.id)})
    assert serializer.is_valid(), serializer.errors

    with patch("apps.registrations.serializers.schedule_event_reminder") as mock_schedule:
        registration = serializer.save()
        assert mock_schedule.called
        assert mock_schedule.call_args[0][0] == registration
