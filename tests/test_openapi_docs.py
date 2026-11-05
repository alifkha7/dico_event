import json
from io import StringIO

from django.conf import settings
from django.core.management import call_command
import pytest
from rest_framework import status


@pytest.mark.django_db
def test_openapi_settings_configuration():
    """Verify drf-spectacular configuration in Django settings."""
    assert 'drf_spectacular' in settings.INSTALLED_APPS
    assert settings.REST_FRAMEWORK.get('DEFAULT_SCHEMA_CLASS') == 'drf_spectacular.openapi.AutoSchema'

    spectacular_settings = getattr(settings, 'SPECTACULAR_SETTINGS', {})
    assert spectacular_settings.get('TITLE') == 'DicoEvent API'
    assert spectacular_settings.get('DESCRIPTION') == 'RESTful API for the DicoEvent Event Management and Ticketing Platform.'
    assert spectacular_settings.get('VERSION') == '2.0.0'
    assert spectacular_settings.get('SERVE_INCLUDE_SCHEMA') is False
    assert spectacular_settings.get('SERVE_PERMISSIONS') == ['rest_framework.permissions.AllowAny']
    assert spectacular_settings.get('COMPONENT_SPLIT_REQUEST') is True


@pytest.mark.django_db
@pytest.mark.parametrize('url', ['/api/schema/', '/api/schema'])
def test_schema_endpoint_unauthenticated_and_trailing_slashes(api_client, url):
    """Verify unauthenticated GET to /api/schema/ and /api/schema returns 200 OK."""
    response = api_client.get(url, HTTP_ACCEPT='application/json')
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.parametrize('url', ['/api/docs/', '/api/docs'])
def test_swagger_ui_endpoint_unauthenticated_and_trailing_slashes(api_client, url):
    """Verify unauthenticated GET to /api/docs/ and /api/docs returns 200 OK and Swagger UI HTML."""
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    content = response.content.decode('utf-8')
    assert 'swagger' in content.lower() or 'swagger-ui' in content.lower()


@pytest.mark.django_db
@pytest.mark.parametrize('url', ['/api/redoc/', '/api/redoc'])
def test_redoc_endpoint_unauthenticated_and_trailing_slashes(api_client, url):
    """Verify unauthenticated GET to /api/redoc/ and /api/redoc returns 200 OK and Redoc HTML."""
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    content = response.content.decode('utf-8')
    assert 'redoc' in content.lower()


@pytest.mark.django_db
def test_openapi_schema_structure_and_paths(api_client):
    """Parse OpenAPI schema and verify title, version, and required resource paths."""
    response = api_client.get('/api/schema/', HTTP_ACCEPT='application/json')
    assert response.status_code == status.HTTP_200_OK

    schema = json.loads(response.content.decode('utf-8'))

    # Verify OpenAPI 3.0+
    assert schema.get('openapi', '').startswith('3.')

    # Verify info
    info = schema.get('info', {})
    assert info.get('title') == 'DicoEvent API'
    assert info.get('version') == '2.0.0'

    # Verify documented paths include required endpoints
    paths = schema.get('paths', {})
    required_path_substrings = [
        '/api/login',
        '/api/token',
        '/api/users',
        '/api/groups',
        '/api/assign-roles',
        '/api/events',
        '/api/events/upload',
        '/api/tickets',
        '/api/registrations',
        '/api/payments',
    ]

    for req in required_path_substrings:
        matching = [p for p in paths if p.startswith(req) or p.rstrip('/') == req]
        assert matching, f"Required endpoint path '{req}' missing from OpenAPI schema paths: {list(paths)}"

    # Verify components and schemas
    components = schema.get('components', {})
    schemas = components.get('schemas', {})
    assert 'AssignRoleResponse' in schemas
    assert 'EventPoster' in schemas
    assert 'Event' in schemas
    assert 'Ticket' in schemas
    assert 'Registration' in schemas
    assert 'Payment' in schemas


@pytest.mark.django_db
def test_spectacular_validate_management_command():
    """Verify that django-admin/manage.py spectacular --validate runs without raising errors."""
    out = StringIO()
    call_command('spectacular', '--validate', stdout=out)
    output = out.getvalue()
    assert 'openapi: 3.' in output
