import os

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

# Ensure fast SQLite in-memory and local memory cache for testing
os.environ["USE_SQLITE_TEST"] = "True"
os.environ.setdefault("DJANGO_ENV", "test")


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """Autouse fixture to isolate cache between all test cases."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def superuser(db):
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="Aras",
        defaults={
            "email": "aras@dicoevent.com",
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )
    user.set_password("1234qwer!@#$")
    user.save()
    return user


@pytest.fixture
def admin_group(db):
    group, _ = Group.objects.get_or_create(name="admin")
    return group


@pytest.fixture
def organizer_group(db):
    group, _ = Group.objects.get_or_create(name="organizer")
    return group


@pytest.fixture
def admin_user(db, admin_group):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_user",
        email="admin@dicoevent.com",
        password="password123",
    )
    user.groups.add(admin_group)
    return user


@pytest.fixture
def organizer_user(db, organizer_group):
    User = get_user_model()
    user = User.objects.create_user(
        username="organizer_user",
        email="organizer@dicoevent.com",
        password="password123",
    )
    user.groups.add(organizer_group)
    return user


@pytest.fixture
def regular_user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="regular_user",
        email="user@dicoevent.com",
        password="password123",
    )


@pytest.fixture
def get_auth_header():
    def _get_auth_header(user):
        refresh = RefreshToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"}

    return _get_auth_header
