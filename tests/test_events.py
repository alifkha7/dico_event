import uuid
from datetime import datetime, timezone, timedelta
import pytest
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def another_organizer(db, organizer_group):
    user = User.objects.create_user(
        username='another_organizer',
        email='organizer2@dicoevent.com',
        password='password123',
    )
    user.groups.add(organizer_group)
    return user

@pytest.fixture
def sample_event_data(organizer_user):
    now = datetime.now(timezone.utc)
    return {
        'name': 'Tech Summit 2026',
        'description': 'A premier technology conference.',
        'location': 'Jakarta Convention Center',
        'start_time': (now + timedelta(days=10)).isoformat(),
        'end_time': (now + timedelta(days=11)).isoformat(),
        'status': 'published',
        'quota': 500,
        'category': 'Technology',
        'organizer_id': str(organizer_user.id),
    }

# ==========================================
# 1. Event Creation & RBAC Permissions (POST)
# ==========================================

@pytest.mark.django_db
def test_create_event_superuser(api_client, superuser, organizer_user, get_auth_header, sample_event_data):
    """Verify Superuser can create an event and receive 201 Created with full attributes."""
    headers = get_auth_header(superuser)
    response = api_client.post('/api/events/', sample_event_data, format='json', **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert 'id' in response.data
    assert uuid.UUID(response.data['id'])
    assert response.data['name'] == sample_event_data['name']
    assert response.data['description'] == sample_event_data['description']
    assert response.data['location'] == sample_event_data['location']
    assert response.data['status'] == sample_event_data['status']
    assert response.data['quota'] == 500
    assert isinstance(response.data['quota'], int)
    assert response.data['category'] == sample_event_data['category']
    assert response.data['organizer_id'] == str(organizer_user.id)
    assert response.data['organizer'] == str(organizer_user.id)

@pytest.mark.django_db
def test_create_event_admin(api_client, admin_user, get_auth_header, sample_event_data):
    """Verify Admin can create an event."""
    headers = get_auth_header(admin_user)
    response = api_client.post('/api/events/', sample_event_data, format='json', **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['name'] == sample_event_data['name']

@pytest.mark.django_db
def test_create_event_organizer_defaults_to_self(api_client, organizer_user, get_auth_header, sample_event_data):
    """Verify Organizer can create an event; if organizer_id is omitted, defaults to authenticated user."""
    headers = get_auth_header(organizer_user)
    data = sample_event_data.copy()
    data.pop('organizer_id', None)
    response = api_client.post('/api/events/', data, format='json', **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['organizer_id'] == str(organizer_user.id)
    assert response.data['organizer'] == str(organizer_user.id)

@pytest.mark.django_db
def test_create_event_no_trailing_slash(api_client, organizer_user, get_auth_header, sample_event_data):
    """Verify POST /api/events (no trailing slash) succeeds per ADR-0001."""
    headers = get_auth_header(organizer_user)
    response = api_client.post('/api/events', sample_event_data, format='json', **headers)
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_create_event_regular_user_forbidden(api_client, regular_user, get_auth_header, sample_event_data):
    """Verify standard User cannot create an event (403 Forbidden)."""
    headers = get_auth_header(regular_user)
    response = api_client.post('/api/events/', sample_event_data, format='json', **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_create_event_unauthenticated(api_client, sample_event_data):
    """Verify unauthenticated request cannot create an event (401 Unauthorized)."""
    response = api_client.post('/api/events/', sample_event_data, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# ==========================================
# 2. Event Listing, Query Params & Pagination (GET)
# ==========================================

@pytest.mark.django_db
def test_list_events_unauthenticated_and_authenticated(api_client, organizer_user, regular_user, get_auth_header, sample_event_data):
    """Verify GET /api/events/ is accessible to both unauthenticated and authenticated users."""
    # Create an event first
    headers_org = get_auth_header(organizer_user)
    api_client.post('/api/events/', sample_event_data, format='json', **headers_org)

    # Unauthenticated GET
    res_unauth = api_client.get('/api/events/')
    assert res_unauth.status_code == status.HTTP_200_OK
    assert 'events' in res_unauth.data
    assert isinstance(res_unauth.data['events'], list)
    assert len(res_unauth.data['events']) >= 1

    # Authenticated User GET
    headers_user = get_auth_header(regular_user)
    res_auth = api_client.get('/api/events/', **headers_user)
    assert res_auth.status_code == status.HTTP_200_OK
    assert 'events' in res_auth.data
    assert isinstance(res_auth.data['events'], list)

@pytest.mark.django_db
def test_list_events_no_trailing_slash(api_client):
    """Verify GET /api/events (no trailing slash) returns 200 OK."""
    response = api_client.get('/api/events')
    assert response.status_code == status.HTTP_200_OK
    assert 'events' in response.data

@pytest.mark.django_db
def test_list_events_pagination(api_client, organizer_user, get_auth_header, sample_event_data):
    """Verify ?page=1 pagination wraps results in {'events': [...]} alongside pagination metadata."""
    headers = get_auth_header(organizer_user)
    now = datetime.now(timezone.utc)
    # Create 15 events
    for i in range(15):
        data = sample_event_data.copy()
        data['name'] = f"Event Number {i:02d}"
        data['start_time'] = (now + timedelta(days=i + 1)).isoformat()
        data['end_time'] = (now + timedelta(days=i + 2)).isoformat()
        api_client.post('/api/events/', data, format='json', **headers)

    # Page 1
    res_p1 = api_client.get('/api/events/?page=1')
    assert res_p1.status_code == status.HTTP_200_OK
    assert 'events' in res_p1.data
    assert isinstance(res_p1.data['events'], list)
    assert len(res_p1.data['events']) == 10
    assert res_p1.data.get('count') == 15
    assert res_p1.data.get('next') is not None
    assert res_p1.data.get('previous') is None

    # Page 2
    res_p2 = api_client.get('/api/events/?page=2')
    assert res_p2.status_code == status.HTTP_200_OK
    assert 'events' in res_p2.data
    assert len(res_p2.data['events']) == 5
    assert res_p2.data.get('next') is None
    assert res_p2.data.get('previous') is not None

@pytest.mark.django_db
def test_list_events_filtering(api_client, organizer_user, get_auth_header, sample_event_data):
    """Verify filtering by ?category=..., ?status=..., and ?name=... works properly."""
    headers = get_auth_header(organizer_user)
    now = datetime.now(timezone.utc)

    # Create Event A: Category Music, status published
    data_a = sample_event_data.copy()
    data_a['name'] = "Jazz Concert Live"
    data_a['category'] = "Music"
    data_a['status'] = "published"
    api_client.post('/api/events/', data_a, format='json', **headers)

    # Create Event B: Category Tech, status draft
    data_b = sample_event_data.copy()
    data_b['name'] = "AI Hackathon"
    data_b['category'] = "Tech"
    data_b['status'] = "draft"
    api_client.post('/api/events/', data_b, format='json', **headers)

    # Filter by category=Music
    res_cat = api_client.get('/api/events/?category=Music')
    assert res_cat.status_code == status.HTTP_200_OK
    assert len(res_cat.data['events']) == 1
    assert res_cat.data['events'][0]['name'] == "Jazz Concert Live"

    # Filter by status=draft
    res_stat = api_client.get('/api/events/?status=draft')
    assert res_stat.status_code == status.HTTP_200_OK
    assert len(res_stat.data['events']) == 1
    assert res_stat.data['events'][0]['name'] == "AI Hackathon"

    # Filter by name contains
    res_name = api_client.get('/api/events/?name=Hackathon')
    assert res_name.status_code == status.HTTP_200_OK
    assert len(res_name.data['events']) == 1
    assert res_name.data['events'][0]['name'] == "AI Hackathon"

@pytest.mark.django_db
def test_list_events_ordering_and_search(api_client, organizer_user, get_auth_header, sample_event_data):
    """Verify ?search=... and ?ordering=... work as expected."""
    headers = get_auth_header(organizer_user)

    data_1 = sample_event_data.copy()
    data_1['name'] = "Alpha Meetup"
    data_1['quota'] = 100
    api_client.post('/api/events/', data_1, format='json', **headers)

    data_2 = sample_event_data.copy()
    data_2['name'] = "Beta Workshop"
    data_2['quota'] = 50
    api_client.post('/api/events/', data_2, format='json', **headers)

    # Search for "Alpha"
    res_search = api_client.get('/api/events/?search=Alpha')
    assert res_search.status_code == status.HTTP_200_OK
    assert len(res_search.data['events']) == 1
    assert res_search.data['events'][0]['name'] == "Alpha Meetup"

    # Order by quota ascending
    res_order = api_client.get('/api/events/?ordering=quota')
    assert res_order.status_code == status.HTTP_200_OK
    quotas = [e['quota'] for e in res_order.data['events']]
    assert quotas == sorted(quotas)

# ==========================================
# 3. Event Detail & ADR-0001 (GET <id>)
# ==========================================

@pytest.mark.django_db
def test_retrieve_event_allow_any(api_client, organizer_user, get_auth_header, sample_event_data):
    """Verify unauthenticated GET /api/events/<id>/ succeeds per ADR-0001."""
    headers = get_auth_header(organizer_user)
    res_create = api_client.post('/api/events/', sample_event_data, format='json', **headers)
    event_id = res_create.data['id']

    # Unauthenticated GET with trailing slash
    res_get = api_client.get(f'/api/events/{event_id}/')
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.data['id'] == event_id
    assert res_get.data['name'] == sample_event_data['name']

    # Unauthenticated GET without trailing slash per ADR-0001
    res_get_no_slash = api_client.get(f'/api/events/{event_id}')
    assert res_get_no_slash.status_code == status.HTTP_200_OK
    assert res_get_no_slash.data['id'] == event_id

@pytest.mark.django_db
def test_retrieve_event_not_found(api_client):
    """Verify non-existent UUID returns 404 Not Found."""
    random_uuid = str(uuid.uuid4())
    response = api_client.get(f'/api/events/{random_uuid}/')
    assert response.status_code == status.HTTP_404_NOT_FOUND

# ==========================================
# 4. Event Update & Ownership RBAC (PUT)
# ==========================================

@pytest.mark.django_db
def test_update_event_superuser_and_admin(api_client, superuser, admin_user, organizer_user, get_auth_header, sample_event_data):
    """Verify Superuser and Admin can update any event."""
    # Created by Organizer
    res_create = api_client.post('/api/events/', sample_event_data, format='json', **get_auth_header(organizer_user))
    event_id = res_create.data['id']

    # Superuser updates
    res_su = api_client.put(
        f'/api/events/{event_id}/',
        {'name': 'Superuser Updated Title'},
        format='json',
        **get_auth_header(superuser)
    )
    assert res_su.status_code == status.HTTP_200_OK
    assert res_su.data['name'] == 'Superuser Updated Title'

    # Admin updates
    res_adm = api_client.put(
        f'/api/events/{event_id}/',
        {'name': 'Admin Updated Title'},
        format='json',
        **get_auth_header(admin_user)
    )
    assert res_adm.status_code == status.HTTP_200_OK
    assert res_adm.data['name'] == 'Admin Updated Title'

@pytest.mark.django_db
def test_update_event_organizer_own_event(api_client, organizer_user, get_auth_header, sample_event_data):
    """Verify Organizer can update their own event with partial fields and optional trailing slash."""
    headers = get_auth_header(organizer_user)
    res_create = api_client.post('/api/events/', sample_event_data, format='json', **headers)
    event_id = res_create.data['id']

    # PUT without trailing slash
    res_put = api_client.put(
        f'/api/events/{event_id}',
        {'name': 'Organizer New Title', 'quota': 600},
        format='json',
        **headers
    )
    assert res_put.status_code == status.HTTP_200_OK
    assert res_put.data['name'] == 'Organizer New Title'
    assert res_put.data['quota'] == 600

@pytest.mark.django_db
def test_update_event_organizer_other_event_forbidden(api_client, organizer_user, another_organizer, get_auth_header, sample_event_data):
    """Verify Organizer A cannot update Organizer B's event (403 Forbidden)."""
    # Event created by organizer_user
    res_create = api_client.post('/api/events/', sample_event_data, format='json', **get_auth_header(organizer_user))
    event_id = res_create.data['id']

    # another_organizer attempts PUT
    res_put = api_client.put(
        f'/api/events/{event_id}/',
        {'name': 'Hacked Title'},
        format='json',
        **get_auth_header(another_organizer)
    )
    assert res_put.status_code == status.HTTP_403_FORBIDDEN

    # Verify event unchanged
    res_get = api_client.get(f'/api/events/{event_id}/')
    assert res_get.data['name'] == sample_event_data['name']

@pytest.mark.django_db
def test_update_event_regular_user_forbidden(api_client, organizer_user, regular_user, get_auth_header, sample_event_data):
    """Verify regular User cannot update an event (403 Forbidden)."""
    res_create = api_client.post('/api/events/', sample_event_data, format='json', **get_auth_header(organizer_user))
    event_id = res_create.data['id']

    res_put = api_client.put(
        f'/api/events/{event_id}/',
        {'name': 'User Tampering'},
        format='json',
        **get_auth_header(regular_user)
    )
    assert res_put.status_code == status.HTTP_403_FORBIDDEN

# ==========================================
# 5. Event Deletion & Ownership RBAC (DELETE)
# ==========================================

@pytest.mark.django_db
def test_delete_event_superuser_and_admin(api_client, superuser, admin_user, organizer_user, get_auth_header, sample_event_data):
    """Verify Superuser and Admin can delete any event and subsequent GET returns 404."""
    # Delete by Superuser
    res1 = api_client.post('/api/events/', sample_event_data, format='json', **get_auth_header(organizer_user))
    ev1_id = res1.data['id']
    res_del1 = api_client.delete(f'/api/events/{ev1_id}/', **get_auth_header(superuser))
    assert res_del1.status_code == status.HTTP_204_NO_CONTENT
    assert api_client.get(f'/api/events/{ev1_id}/').status_code == status.HTTP_404_NOT_FOUND

    # Delete by Admin
    res2 = api_client.post('/api/events/', sample_event_data, format='json', **get_auth_header(organizer_user))
    ev2_id = res2.data['id']
    res_del2 = api_client.delete(f'/api/events/{ev2_id}/', **get_auth_header(admin_user))
    assert res_del2.status_code == status.HTTP_204_NO_CONTENT
    assert api_client.get(f'/api/events/{ev2_id}/').status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_delete_event_organizer_own_event(api_client, organizer_user, get_auth_header, sample_event_data):
    """Verify Organizer can delete their own event (204 No Content)."""
    headers = get_auth_header(organizer_user)
    res_create = api_client.post('/api/events/', sample_event_data, format='json', **headers)
    event_id = res_create.data['id']

    # Delete without trailing slash
    res_del = api_client.delete(f'/api/events/{event_id}', **headers)
    assert res_del.status_code == status.HTTP_204_NO_CONTENT
    assert api_client.get(f'/api/events/{event_id}/').status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_delete_event_organizer_other_event_forbidden(api_client, organizer_user, another_organizer, get_auth_header, sample_event_data):
    """Verify Organizer A cannot delete Organizer B's event (403 Forbidden)."""
    res_create = api_client.post('/api/events/', sample_event_data, format='json', **get_auth_header(organizer_user))
    event_id = res_create.data['id']

    # another_organizer tries DELETE
    res_del = api_client.delete(f'/api/events/{event_id}/', **get_auth_header(another_organizer))
    assert res_del.status_code == status.HTTP_403_FORBIDDEN

    # Event must still exist
    assert api_client.get(f'/api/events/{event_id}/').status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_delete_event_regular_user_forbidden(api_client, organizer_user, regular_user, get_auth_header, sample_event_data):
    """Verify standard User cannot delete an event (403 Forbidden)."""
    res_create = api_client.post('/api/events/', sample_event_data, format='json', **get_auth_header(organizer_user))
    event_id = res_create.data['id']

    res_del = api_client.delete(f'/api/events/{event_id}/', **get_auth_header(regular_user))
    assert res_del.status_code == status.HTTP_403_FORBIDDEN
    assert api_client.get(f'/api/events/{event_id}/').status_code == status.HTTP_200_OK
