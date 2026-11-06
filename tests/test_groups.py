import uuid

import pytest
from django.contrib.auth.models import Group
from rest_framework import status


@pytest.mark.django_db
def test_create_group_superuser(api_client, superuser, get_auth_header):
    """Verify Superuser can create role groups with numeric id > 0."""
    headers = get_auth_header(superuser)
    data = {"name": "test_role"}
    response = api_client.post("/api/groups/", data, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert isinstance(response.data["id"], int)
    assert response.data["id"] > 0
    assert response.data["name"] == "test_role"


@pytest.mark.django_db
def test_create_group_no_trailing_slash(api_client, superuser, get_auth_header):
    """Verify Superuser can create group on /api/groups (no trailing slash)."""
    headers = get_auth_header(superuser)
    data = {"name": "test_role_no_slash"}
    response = api_client.post("/api/groups", data, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "test_role_no_slash"


@pytest.mark.django_db
def test_create_group_forbidden_for_admin_and_user(api_client, admin_user, regular_user, get_auth_header):
    """Verify Admin and standard User cannot create groups (403 Forbidden)."""
    data = {"name": "unauthorized_group"}

    admin_headers = get_auth_header(admin_user)
    res_admin = api_client.post("/api/groups/", data, format="json", **admin_headers)
    assert res_admin.status_code == status.HTTP_403_FORBIDDEN

    user_headers = get_auth_header(regular_user)
    res_user = api_client.post("/api/groups/", data, format="json", **user_headers)
    assert res_user.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_list_groups_superuser(api_client, superuser, admin_group, get_auth_header):
    """Verify Superuser can list groups wrapped in {'groups': [...]}."""
    headers = get_auth_header(superuser)
    response = api_client.get("/api/groups/", **headers)
    assert response.status_code == status.HTTP_200_OK
    assert "groups" in response.data
    assert isinstance(response.data["groups"], list)
    assert len(response.data["groups"]) >= 1


@pytest.mark.django_db
def test_list_groups_forbidden_for_admin_and_user(api_client, admin_user, regular_user, get_auth_header):
    """Verify Admin and regular User cannot list groups."""
    admin_headers = get_auth_header(admin_user)
    res_admin = api_client.get("/api/groups/", **admin_headers)
    assert res_admin.status_code == status.HTTP_403_FORBIDDEN

    user_headers = get_auth_header(regular_user)
    res_user = api_client.get("/api/groups/", **user_headers)
    assert res_user.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_group_crud_lifecycle(api_client, superuser, get_auth_header):
    """Verify Superuser can retrieve, update, and delete group."""
    headers = get_auth_header(superuser)
    group = Group.objects.create(name="temporary_group")

    # Retrieve with trailing slash
    get_res = api_client.get(f"/api/groups/{group.id}/", **headers)
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.data["name"] == "temporary_group"

    # Retrieve without trailing slash
    get_res2 = api_client.get(f"/api/groups/{group.id}", **headers)
    assert get_res2.status_code == status.HTTP_200_OK

    # Update
    put_res = api_client.put(f"/api/groups/{group.id}/", {"name": "updated_group"}, format="json", **headers)
    assert put_res.status_code == status.HTTP_200_OK
    assert put_res.data["name"] == "updated_group"

    # Delete
    del_res = api_client.delete(f"/api/groups/{group.id}/", **headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # Subsequent GET returns 404
    subsequent_res = api_client.get(f"/api/groups/{group.id}/", **headers)
    assert subsequent_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_assign_roles_superuser(api_client, superuser, regular_user, admin_group, get_auth_header):
    """Verify Superuser can assign a user to a group via POST /api/assign-roles/."""
    headers = get_auth_header(superuser)
    payload = {
        "user_id": str(regular_user.id),
        "group_id": admin_group.id,
    }
    response = api_client.post("/api/assign-roles/", payload, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert "message" in response.data
    assert response.data["user_id"] == str(regular_user.id)
    assert response.data["group_id"] == admin_group.id

    # Verify user now has the group
    regular_user.refresh_from_db()
    assert regular_user.groups.filter(id=admin_group.id).exists()


@pytest.mark.django_db
def test_assign_roles_no_trailing_slash(api_client, superuser, regular_user, organizer_group, get_auth_header):
    """Verify POST /api/assign-roles (no trailing slash) works."""
    headers = get_auth_header(superuser)
    payload = {
        "user_id": str(regular_user.id),
        "group_id": organizer_group.id,
    }
    response = api_client.post("/api/assign-roles", payload, format="json", **headers)
    assert response.status_code == status.HTTP_201_CREATED

    regular_user.refresh_from_db()
    assert regular_user.groups.filter(id=organizer_group.id).exists()


@pytest.mark.django_db
def test_assign_roles_forbidden_for_admin_and_user(api_client, admin_user, regular_user, admin_group, get_auth_header):
    """Verify Admin and standard User get 403 Forbidden on assign-roles."""
    payload = {
        "user_id": str(regular_user.id),
        "group_id": admin_group.id,
    }
    admin_headers = get_auth_header(admin_user)
    res_admin = api_client.post("/api/assign-roles/", payload, format="json", **admin_headers)
    assert res_admin.status_code == status.HTTP_403_FORBIDDEN

    user_headers = get_auth_header(regular_user)
    res_user = api_client.post("/api/assign-roles/", payload, format="json", **user_headers)
    assert res_user.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_assign_roles_invalid_ids(api_client, superuser, regular_user, get_auth_header):
    """Verify invalid user_id or group_id returns 400 Bad Request."""
    headers = get_auth_header(superuser)

    # Invalid user
    res1 = api_client.post(
        "/api/assign-roles/",
        {
            "user_id": str(uuid.uuid4()),
            "group_id": 1,
        },
        format="json",
        **headers,
    )
    assert res1.status_code == status.HTTP_400_BAD_REQUEST

    # Invalid group
    res2 = api_client.post(
        "/api/assign-roles/",
        {
            "user_id": str(regular_user.id),
            "group_id": 999999,
        },
        format="json",
        **headers,
    )
    assert res2.status_code == status.HTTP_400_BAD_REQUEST
