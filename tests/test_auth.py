import pytest
from datetime import timedelta
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from django.conf import settings

@pytest.mark.django_db
def test_preseeded_superuser_login(api_client, superuser):
    """Verify pre-seeded superuser Aras can log in via POST /api/login/."""
    response = api_client.post('/api/login/', {
        'username': 'Aras',
        'password': '1234qwer!@#$',
    }, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data
    assert 'refresh' in response.data

    # Verify access token lifetime is 3 hours
    access_token = AccessToken(response.data['access'])
    exp = access_token['exp']
    iat = access_token['iat']
    diff_seconds = exp - iat
    assert abs(diff_seconds - 3 * 3600) <= 2

@pytest.mark.django_db
def test_login_without_trailing_slash(api_client, regular_user):
    """Verify POST /api/login (no trailing slash) works per ADR-0001."""
    response = api_client.post('/api/login', {
        'username': regular_user.username,
        'password': 'password123',
    }, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data
    assert 'refresh' in response.data

@pytest.mark.django_db
def test_login_invalid_credentials(api_client, regular_user):
    """Verify login with invalid password returns 401 Unauthorized."""
    response = api_client.post('/api/login/', {
        'username': regular_user.username,
        'password': 'wrongpassword',
    }, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_token_refresh(api_client, regular_user):
    """Verify POST /api/token/ refreshes access token."""
    login_res = api_client.post('/api/login/', {
        'username': regular_user.username,
        'password': 'password123',
    }, format='json')
    refresh_token = login_res.data['refresh']

    refresh_res = api_client.post('/api/token/', {
        'refresh': refresh_token,
    }, format='json')
    assert refresh_res.status_code == status.HTTP_200_OK
    assert 'access' in refresh_res.data

@pytest.mark.django_db
def test_token_refresh_invalid(api_client):
    """Verify refresh with invalid token returns 401 Unauthorized."""
    response = api_client.post('/api/token/', {
        'refresh': 'invalid.token.here',
    }, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
