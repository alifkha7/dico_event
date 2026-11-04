import uuid
from datetime import datetime, timezone, timedelta
import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.cache import cache

from api.models import Event

User = get_user_model()

@pytest.fixture
def sample_event_payload(organizer_user):
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

@pytest.fixture
def created_event(db, organizer_user):
    now = datetime.now(timezone.utc)
    return Event.objects.create(
        name='Original Event Title',
        description='Event description',
        location='Bandung',
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status='published',
        quota=200,
        category='Technology',
        organizer=organizer_user,
    )

# =========================================================================
# 1. Event Detail Retrieval Caching (GET /api/events/<id>/)
# =========================================================================

@pytest.mark.django_db
def test_retrieve_event_cache_miss_then_hit(api_client, created_event):
    """Verify first GET /api/events/<id>/ returns database, second returns cache."""
    event_id = str(created_event.id)

    # 1. First request: Cache miss -> X-Data-Source: database
    res1 = api_client.get(f'/api/events/{event_id}/')
    assert res1.status_code == status.HTTP_200_OK
    assert res1.headers.get('X-Data-Source') == 'database'
    assert res1.data['id'] == event_id
    assert res1.data['name'] == created_event.name

    # 2. Second request: Cache hit -> X-Data-Source: cache
    res2 = api_client.get(f'/api/events/{event_id}/')
    assert res2.status_code == status.HTTP_200_OK
    assert res2.headers.get('X-Data-Source') == 'cache'
    assert res2.data['id'] == event_id
    assert res2.data['name'] == created_event.name

@pytest.mark.django_db
def test_retrieve_event_not_found_not_cached(api_client):
    """Verify 404 is not cached."""
    missing_id = str(uuid.uuid4())
    res = api_client.get(f'/api/events/{missing_id}/')
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert cache.get(f"events:detail:{missing_id}") is None

# =========================================================================
# 2. Event List Caching (GET /api/events/)
# =========================================================================

@pytest.mark.django_db
def test_list_events_cache_miss_then_hit(api_client, created_event):
    """Verify first GET /api/events/ returns database, second returns cache."""
    # 1. First request: Cache miss -> X-Data-Source: database
    res1 = api_client.get('/api/events/')
    assert res1.status_code == status.HTTP_200_OK
    assert res1.headers.get('X-Data-Source') == 'database'
    assert 'events' in res1.data
    assert len(res1.data['events']) >= 1

    # 2. Second request: Cache hit -> X-Data-Source: cache
    res2 = api_client.get('/api/events/')
    assert res2.status_code == status.HTTP_200_OK
    assert res2.headers.get('X-Data-Source') == 'cache'
    assert 'events' in res2.data
    assert res2.data == res1.data

@pytest.mark.django_db
def test_list_events_query_params_caching(api_client, created_event, organizer_user):
    """Verify query string variations (?category=..., ?page=...) are cached independently."""
    # Query with category=Technology
    res1 = api_client.get('/api/events/?category=Technology')
    assert res1.status_code == status.HTTP_200_OK
    assert res1.headers.get('X-Data-Source') == 'database'

    res2 = api_client.get('/api/events/?category=Technology')
    assert res2.status_code == status.HTTP_200_OK
    assert res2.headers.get('X-Data-Source') == 'cache'

    # Query with category=Music (different query string)
    res_diff1 = api_client.get('/api/events/?category=Music')
    assert res_diff1.status_code == status.HTTP_200_OK
    assert res_diff1.headers.get('X-Data-Source') == 'database'

    res_diff2 = api_client.get('/api/events/?category=Music')
    assert res_diff2.status_code == status.HTTP_200_OK
    assert res_diff2.headers.get('X-Data-Source') == 'cache'

# =========================================================================
# 3. Cache Invalidation on Event Mutations (POST, PUT, DELETE)
# =========================================================================

@pytest.mark.django_db
def test_post_event_invalidates_list_cache(api_client, organizer_user, get_auth_header, sample_event_payload):
    """Verify POST /api/events/ invalidates list cache."""
    # Populate list cache
    res_init = api_client.get('/api/events/')
    assert res_init.headers.get('X-Data-Source') == 'database'
    res_cached = api_client.get('/api/events/')
    assert res_cached.headers.get('X-Data-Source') == 'cache'

    # Create new event
    headers = get_auth_header(organizer_user)
    res_post = api_client.post('/api/events/', sample_event_payload, format='json', **headers)
    assert res_post.status_code == status.HTTP_201_CREATED

    # Next list request must hit database
    res_after = api_client.get('/api/events/')
    assert res_after.status_code == status.HTTP_200_OK
    assert res_after.headers.get('X-Data-Source') == 'database'
    assert any(e['id'] == res_post.data['id'] for e in res_after.data['events'])

    # Subsequent request is cached
    res_cached_after = api_client.get('/api/events/')
    assert res_cached_after.headers.get('X-Data-Source') == 'cache'

@pytest.mark.django_db
def test_put_event_invalidates_detail_and_list_cache(api_client, organizer_user, get_auth_header, created_event):
    """Verify PUT /api/events/<id>/ invalidates both detail and list caches."""
    event_id = str(created_event.id)
    headers = get_auth_header(organizer_user)

    # Populate detail and list caches
    api_client.get(f'/api/events/{event_id}/')
    assert api_client.get(f'/api/events/{event_id}/').headers.get('X-Data-Source') == 'cache'
    api_client.get('/api/events/')
    assert api_client.get('/api/events/').headers.get('X-Data-Source') == 'cache'

    # Update event
    res_put = api_client.put(
        f'/api/events/{event_id}/',
        {'name': 'Updated Title After Invalidation'},
        format='json',
        **headers
    )
    assert res_put.status_code == status.HTTP_200_OK
    assert res_put.data['name'] == 'Updated Title After Invalidation'

    # Detail must be database miss
    res_detail = api_client.get(f'/api/events/{event_id}/')
    assert res_detail.status_code == status.HTTP_200_OK
    assert res_detail.headers.get('X-Data-Source') == 'database'
    assert res_detail.data['name'] == 'Updated Title After Invalidation'

    # Subsequent detail is cache
    assert api_client.get(f'/api/events/{event_id}/').headers.get('X-Data-Source') == 'cache'

    # List must be database miss
    res_list = api_client.get('/api/events/')
    assert res_list.status_code == status.HTTP_200_OK
    assert res_list.headers.get('X-Data-Source') == 'database'
    matching = [e for e in res_list.data['events'] if e['id'] == event_id]
    assert len(matching) == 1
    assert matching[0]['name'] == 'Updated Title After Invalidation'

    # Subsequent list is cache
    assert api_client.get('/api/events/').headers.get('X-Data-Source') == 'cache'

@pytest.mark.django_db
def test_delete_event_invalidates_detail_and_list_cache(api_client, organizer_user, get_auth_header, created_event):
    """Verify DELETE /api/events/<id>/ invalidates both detail and list caches."""
    event_id = str(created_event.id)
    headers = get_auth_header(organizer_user)

    # Populate detail and list caches
    api_client.get(f'/api/events/{event_id}/')
    assert api_client.get(f'/api/events/{event_id}/').headers.get('X-Data-Source') == 'cache'
    api_client.get('/api/events/')
    assert api_client.get('/api/events/').headers.get('X-Data-Source') == 'cache'

    # Delete event
    res_del = api_client.delete(f'/api/events/{event_id}/', **headers)
    assert res_del.status_code == status.HTTP_204_NO_CONTENT

    # Detail lookup returns 404 (not served from cache!)
    res_detail = api_client.get(f'/api/events/{event_id}/')
    assert res_detail.status_code == status.HTTP_404_NOT_FOUND

    # List lookup returns database miss without the deleted event
    res_list = api_client.get('/api/events/')
    assert res_list.status_code == status.HTTP_200_OK
    assert res_list.headers.get('X-Data-Source') == 'database'
    assert not any(e['id'] == event_id for e in res_list.data['events'])

    # Subsequent list is cache
    assert api_client.get('/api/events/').headers.get('X-Data-Source') == 'cache'

# =========================================================================
# 4. Complete 15-Step Postman Sequence ([Optional] Caching Events)
# =========================================================================

@pytest.mark.django_db
def test_caching_events_complete_15_step_sequence(api_client, organizer_user, get_auth_header, sample_event_payload, created_event):
    """
    Verify the complete 15-step Postman sequence:
    1. GET /api/events/<id>/ -> 200 OK, X-Data-Source: database
    2. GET /api/events/<id>/ -> 200 OK, X-Data-Source: cache
    3. GET /api/events/ -> 200 OK, X-Data-Source: database
    4. GET /api/events/ -> 200 OK, X-Data-Source: cache
    5. POST /api/events/ -> 201 Created (invalidates list cache)
    6. GET /api/events/ -> 200 OK, X-Data-Source: database
    7. GET /api/events/ -> 200 OK, X-Data-Source: cache
    8. PUT /api/events/<id>/ -> 200 OK (invalidates detail & list cache)
    9. GET /api/events/<id>/ -> 200 OK, X-Data-Source: database
    10. GET /api/events/<id>/ -> 200 OK, X-Data-Source: cache
    11. GET /api/events/ -> 200 OK, X-Data-Source: database
    12. GET /api/events/ -> 200 OK, X-Data-Source: cache
    13. DELETE /api/events/<id>/ -> 204 No Content (invalidates detail & list cache)
    14. GET /api/events/<id>/ -> 404 Not Found
    15. GET /api/events/ -> 200 OK, X-Data-Source: database (deleted event absent),
        followed by GET /api/events/ -> 200 OK, X-Data-Source: cache.
    """
    event_id = str(created_event.id)
    headers = get_auth_header(organizer_user)

    # 1. GET /api/events/<id>/ -> 200 OK, X-Data-Source: database
    s1 = api_client.get(f'/api/events/{event_id}/')
    assert s1.status_code == status.HTTP_200_OK
    assert s1.headers.get('X-Data-Source') == 'database'

    # 2. GET /api/events/<id>/ -> 200 OK, X-Data-Source: cache
    s2 = api_client.get(f'/api/events/{event_id}/')
    assert s2.status_code == status.HTTP_200_OK
    assert s2.headers.get('X-Data-Source') == 'cache'

    # 3. GET /api/events/ -> 200 OK, X-Data-Source: database
    s3 = api_client.get('/api/events/')
    assert s3.status_code == status.HTTP_200_OK
    assert s3.headers.get('X-Data-Source') == 'database'

    # 4. GET /api/events/ -> 200 OK, X-Data-Source: cache
    s4 = api_client.get('/api/events/')
    assert s4.status_code == status.HTTP_200_OK
    assert s4.headers.get('X-Data-Source') == 'cache'

    # 5. POST /api/events/ -> 201 Created (invalidates list cache)
    s5 = api_client.post('/api/events/', sample_event_payload, format='json', **headers)
    assert s5.status_code == status.HTTP_201_CREATED
    new_event_id = s5.data['id']

    # 6. GET /api/events/ -> 200 OK, X-Data-Source: database
    s6 = api_client.get('/api/events/')
    assert s6.status_code == status.HTTP_200_OK
    assert s6.headers.get('X-Data-Source') == 'database'
    assert any(e['id'] == new_event_id for e in s6.data['events'])

    # 7. GET /api/events/ -> 200 OK, X-Data-Source: cache
    s7 = api_client.get('/api/events/')
    assert s7.status_code == status.HTTP_200_OK
    assert s7.headers.get('X-Data-Source') == 'cache'

    # 8. PUT /api/events/<id>/ -> 200 OK (invalidates detail & list cache)
    s8 = api_client.put(
        f'/api/events/{event_id}/',
        {'name': '15-Step Updated Title'},
        format='json',
        **headers
    )
    assert s8.status_code == status.HTTP_200_OK

    # 9. GET /api/events/<id>/ -> 200 OK, X-Data-Source: database
    s9 = api_client.get(f'/api/events/{event_id}/')
    assert s9.status_code == status.HTTP_200_OK
    assert s9.headers.get('X-Data-Source') == 'database'
    assert s9.data['name'] == '15-Step Updated Title'

    # 10. GET /api/events/<id>/ -> 200 OK, X-Data-Source: cache
    s10 = api_client.get(f'/api/events/{event_id}/')
    assert s10.status_code == status.HTTP_200_OK
    assert s10.headers.get('X-Data-Source') == 'cache'

    # 11. GET /api/events/ -> 200 OK, X-Data-Source: database
    s11 = api_client.get('/api/events/')
    assert s11.status_code == status.HTTP_200_OK
    assert s11.headers.get('X-Data-Source') == 'database'

    # 12. GET /api/events/ -> 200 OK, X-Data-Source: cache
    s12 = api_client.get('/api/events/')
    assert s12.status_code == status.HTTP_200_OK
    assert s12.headers.get('X-Data-Source') == 'cache'

    # 13. DELETE /api/events/<id>/ -> 204 No Content (invalidates detail & list cache)
    s13 = api_client.delete(f'/api/events/{event_id}/', **headers)
    assert s13.status_code == status.HTTP_204_NO_CONTENT

    # 14. GET /api/events/<id>/ -> 404 Not Found
    s14 = api_client.get(f'/api/events/{event_id}/')
    assert s14.status_code == status.HTTP_404_NOT_FOUND

    # 15. GET /api/events/ -> 200 OK, X-Data-Source: database (deleted event absent),
    #     followed by GET /api/events/ -> 200 OK, X-Data-Source: cache.
    s15_miss = api_client.get('/api/events/')
    assert s15_miss.status_code == status.HTTP_200_OK
    assert s15_miss.headers.get('X-Data-Source') == 'database'
    assert not any(e['id'] == event_id for e in s15_miss.data['events'])

    s15_hit = api_client.get('/api/events/')
    assert s15_hit.status_code == status.HTTP_200_OK
    assert s15_hit.headers.get('X-Data-Source') == 'cache'
    assert not any(e['id'] == event_id for e in s15_hit.data['events'])
