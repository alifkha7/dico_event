import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
def test_user_registration_allow_any(api_client):
    """Verify POST /api/users/ registers a new user without authentication."""
    data = {
        "username": "newuser1",
        "email": "newuser1@dicoevent.com",
        "password": "SecurePassword123!",
        "first_name": "New",
        "last_name": "User",
    }
    response = api_client.post("/api/users/", data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert "id" in response.data
    # Verify id is a valid UUID
    uuid_obj = uuid.UUID(response.data["id"])
    assert str(uuid_obj) == response.data["id"]
    assert response.data["username"] == "newuser1"
    assert response.data["email"] == "newuser1@dicoevent.com"
    assert response.data["first_name"] == "New"
    assert response.data["last_name"] == "User"
    assert "password" not in response.data

    # Verify password was hashed, not stored plain text
    user = User.objects.get(id=response.data["id"])
    assert user.password != "SecurePassword123!"
    assert user.check_password("SecurePassword123!")


@pytest.mark.django_db
def test_user_registration_no_trailing_slash(api_client):
    """Verify POST /api/users (no trailing slash) registers a user per ADR-0001."""
    data = {
        "username": "newuser2",
        "email": "newuser2@dicoevent.com",
        "password": "SecurePassword123!",
    }
    response = api_client.post("/api/users", data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["username"] == "newuser2"


@pytest.mark.django_db
def test_user_registration_duplicate_username_and_email(api_client, regular_user):
    """Verify duplicate username and email are rejected with 400 Bad Request."""
    data = {
        "username": regular_user.username,
        "email": "different@dicoevent.com",
        "password": "password123",
    }
    res1 = api_client.post("/api/users/", data, format="json")
    assert res1.status_code == status.HTTP_400_BAD_REQUEST

    data2 = {
        "username": "different_name",
        "email": regular_user.email,
        "password": "password123",
    }
    res2 = api_client.post("/api/users/", data2, format="json")
    assert res2.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_list_users_superuser(api_client, superuser, get_auth_header):
    """Verify GET /api/users/ returns 200 OK with {'users': [...]} for Superuser."""
    headers = get_auth_header(superuser)
    response = api_client.get("/api/users/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "users" in response.data
    assert isinstance(response.data["users"], list)
    assert len(response.data["users"]) >= 1


@pytest.mark.django_db
def test_list_users_admin(api_client, admin_user, get_auth_header):
    """Verify GET /api/users/ returns 200 OK with {'users': [...]} for Admin."""
    headers = get_auth_header(admin_user)
    response = api_client.get("/api/users/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "users" in response.data


@pytest.mark.django_db
def test_list_users_regular_user_forbidden(api_client, regular_user, get_auth_header):
    """Verify GET /api/users/ returns 403 Forbidden for standard User."""
    headers = get_auth_header(regular_user)
    response = api_client.get("/api/users/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_users_unauthenticated(api_client):
    """Verify GET /api/users/ returns 401 Unauthorized for unauthenticated requests."""
    response = api_client.get("/api/users/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_retrieve_user_allow_any(api_client, regular_user):
    """Verify GET /api/users/<id>/ allows unauthenticated retrieve per ADR-0001."""
    # With trailing slash
    res1 = api_client.get(f"/api/users/{regular_user.id}/")
    assert res1.status_code == status.HTTP_200_OK
    assert res1.data["id"] == str(regular_user.id)
    assert res1.data["username"] == regular_user.username
    assert res1.data["email"] == regular_user.email

    # Without trailing slash
    res2 = api_client.get(f"/api/users/{regular_user.id}")
    assert res2.status_code == status.HTTP_200_OK
    assert res2.data["id"] == str(regular_user.id)


@pytest.mark.django_db
def test_retrieve_user_not_found(api_client):
    """Verify GET /api/users/<non_existent_uuid>/ returns 404 Not Found."""
    fake_uuid = uuid.uuid4()
    response = api_client.get(f"/api/users/{fake_uuid}/")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_update_user_self_partial_fields(api_client, regular_user, get_auth_header):
    """Verify User can update self with partial fields (e.g. username & password only)."""
    headers = get_auth_header(regular_user)
    update_data = {
        "username": "updated_username",
        "password": "NewSecretPassword123!",
    }
    response = api_client.put(f"/api/users/{regular_user.id}/", update_data, format="json", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["username"] == "updated_username"
    assert response.data["email"] == regular_user.email

    regular_user.refresh_from_db()
    assert regular_user.username == "updated_username"
    assert regular_user.check_password("NewSecretPassword123!")


@pytest.mark.django_db
def test_update_user_by_other_user_forbidden(api_client, regular_user, get_auth_header):
    """Verify regular user cannot update another user's profile."""
    other_user = User.objects.create_user(
        username="other_user",
        email="other@dicoevent.com",
        password="password123",
    )
    headers = get_auth_header(regular_user)
    response = api_client.put(f"/api/users/{other_user.id}/", {"username": "hacked"}, format="json", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_update_user_by_admin(api_client, admin_user, regular_user, get_auth_header):
    """Verify Admin can update any user's profile."""
    headers = get_auth_header(admin_user)
    response = api_client.put(
        f"/api/users/{regular_user.id}/", {"first_name": "AdminUpdatedName"}, format="json", **headers
    )
    assert response.status_code == status.HTTP_200_OK
    regular_user.refresh_from_db()
    assert regular_user.first_name == "AdminUpdatedName"


@pytest.mark.django_db
def test_delete_user_and_subsequent_404(api_client, admin_user, regular_user, get_auth_header):
    """Verify Admin can delete User, returns 204 No Content, subsequent GET returns 404."""
    user_id = regular_user.id
    headers = get_auth_header(admin_user)
    del_res = api_client.delete(f"/api/users/{user_id}/", **headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = api_client.get(f"/api/users/{user_id}/")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_delete_user_by_superuser(api_client, superuser, regular_user, get_auth_header):
    """Verify Superuser can delete User, returns 204 No Content."""
    user_id = regular_user.id
    headers = get_auth_header(superuser)
    del_res = api_client.delete(f"/api/users/{user_id}/", **headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = api_client.get(f"/api/users/{user_id}/")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_delete_user_by_unauthorized_user(api_client, regular_user, admin_user, get_auth_header):
    """Verify standard User cannot delete another User."""
    headers = get_auth_header(regular_user)
    response = api_client.delete(f"/api/users/{admin_user.id}/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_delete_user_self_by_regular_user_forbidden(api_client, regular_user, get_auth_header):
    """Verify standard User cannot delete their own account per Story 9 / Spec (403 Forbidden)."""
    headers = get_auth_header(regular_user)
    response = api_client.delete(f"/api/users/{regular_user.id}/", **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
