import uuid
from datetime import datetime, timezone, timedelta
import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from api.models import Event, Ticket

User = get_user_model()

@pytest.fixture
def sample_event(organizer_user):
    now = datetime.now(timezone.utc)
    return Event.objects.create(
        name='Tech Conference 2026',
        description='Conference description',
        location='Jakarta',
        start_time=now + timedelta(days=5),
        end_time=now + timedelta(days=6),
        status='published',
        quota=200,
        category='Tech',
        organizer=organizer_user,
    )

@pytest.fixture
def sample_ticket_data(sample_event):
    now = datetime.now(timezone.utc)
    return {
        'event_id': str(sample_event.id),
        'name': 'VIP Ticket',
        'price': 150000,
        'sales_start': now.isoformat(),
        'sales_end': (now + timedelta(days=4)).isoformat(),
        'quota': 50,
    }

@pytest.fixture
def sample_ticket(sample_event):
    now = datetime.now(timezone.utc)
    return Ticket.objects.create(
        event=sample_event,
        name='Regular Ticket',
        price=75000,
        sales_start=now,
        sales_end=now + timedelta(days=4),
        quota=100,
    )

# ==========================================
# 1. Ticket Creation & RBAC Permissions (POST)
# ==========================================

@pytest.mark.django_db
def test_create_ticket_superuser(api_client, superuser, get_auth_header, sample_ticket_data):
    """Verify Superuser can create a ticket with event_id."""
    headers = get_auth_header(superuser)
    response = api_client.post('/api/tickets/', sample_ticket_data, format='json', **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert 'id' in response.data
    assert uuid.UUID(response.data['id'])
    assert response.data['name'] == sample_ticket_data['name']
    assert response.data['price'] == 150000
    assert isinstance(response.data['price'], int)
    assert response.data['quota'] == 50
    assert isinstance(response.data['quota'], int)
    assert response.data['event'] == sample_ticket_data['event_id']
    assert response.data['event_id'] == sample_ticket_data['event_id']

@pytest.mark.django_db
def test_create_ticket_admin(api_client, admin_user, get_auth_header, sample_ticket_data):
    """Verify Admin can create a ticket."""
    headers = get_auth_header(admin_user)
    response = api_client.post('/api/tickets/', sample_ticket_data, format='json', **headers)
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_create_ticket_organizer(api_client, organizer_user, get_auth_header, sample_ticket_data):
    """Verify Organizer can create a ticket."""
    headers = get_auth_header(organizer_user)
    response = api_client.post('/api/tickets/', sample_ticket_data, format='json', **headers)
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_create_ticket_accepts_event_field_key(api_client, superuser, get_auth_header, sample_event):
    """Verify ticket creation accepts 'event' key instead of 'event_id'."""
    now = datetime.now(timezone.utc)
    payload = {
        'event': str(sample_event.id),
        'name': 'Early Bird Ticket',
        'price': 50000,
        'sales_start': now.isoformat(),
        'sales_end': (now + timedelta(days=2)).isoformat(),
        'quota': 30,
    }
    headers = get_auth_header(superuser)
    response = api_client.post('/api/tickets/', payload, format='json', **headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['event'] == str(sample_event.id)
    assert response.data['event_id'] == str(sample_event.id)

@pytest.mark.django_db
def test_create_ticket_without_trailing_slash(api_client, organizer_user, get_auth_header, sample_ticket_data):
    """Verify POST /api/tickets (without trailing slash) works per ADR-0001."""
    headers = get_auth_header(organizer_user)
    response = api_client.post('/api/tickets', sample_ticket_data, format='json', **headers)
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_create_ticket_regular_user_forbidden(api_client, regular_user, get_auth_header, sample_ticket_data):
    """Verify standard User cannot create a ticket (403 Forbidden)."""
    headers = get_auth_header(regular_user)
    response = api_client.post('/api/tickets/', sample_ticket_data, format='json', **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_create_ticket_unauthenticated(api_client, sample_ticket_data):
    """Verify unauthenticated user cannot create a ticket (401 Unauthorized)."""
    response = api_client.post('/api/tickets/', sample_ticket_data, format='json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

# ==========================================
# 2. Ticket Listing (GET /api/tickets/)
# ==========================================

@pytest.mark.django_db
def test_list_tickets_envelope(api_client, sample_ticket):
    """Verify GET /api/tickets/ returns 200 OK wrapped in {"tickets": [...]}."""
    response = api_client.get('/api/tickets/')
    assert response.status_code == status.HTTP_200_OK
    assert 'tickets' in response.data
    assert len(response.data['tickets']) >= 1
    assert any(t['id'] == str(sample_ticket.id) for t in response.data['tickets'])

@pytest.mark.django_db
def test_list_tickets_no_trailing_slash(api_client, sample_ticket):
    """Verify GET /api/tickets works without trailing slash."""
    response = api_client.get('/api/tickets')
    assert response.status_code == status.HTTP_200_OK
    assert 'tickets' in response.data

# ==========================================
# 3. Ticket Retrieval (GET /api/tickets/<id>/)
# ==========================================

@pytest.mark.django_db
def test_retrieve_ticket_allow_any(api_client, sample_ticket):
    """Verify unauthenticated GET /api/tickets/<id>/ returns 200 OK per ADR-0001."""
    response = api_client.get(f'/api/tickets/{sample_ticket.id}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['id'] == str(sample_ticket.id)
    assert response.data['event'] == str(sample_ticket.event_id)
    assert response.data['event_id'] == str(sample_ticket.event_id)
    assert response.data['name'] == sample_ticket.name
    assert response.data['price'] == sample_ticket.price
    assert response.data['quota'] == sample_ticket.quota

@pytest.mark.django_db
def test_retrieve_ticket_no_trailing_slash(api_client, sample_ticket):
    """Verify unauthenticated GET /api/tickets/<id> works without trailing slash."""
    response = api_client.get(f'/api/tickets/{sample_ticket.id}')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['id'] == str(sample_ticket.id)

@pytest.mark.django_db
def test_retrieve_ticket_not_found(api_client):
    """Verify GET /api/tickets/<nonexistent_id>/ returns 404 Not Found."""
    random_id = uuid.uuid4()
    response = api_client.get(f'/api/tickets/{random_id}/')
    assert response.status_code == status.HTTP_404_NOT_FOUND

# ==========================================
# 4. Ticket Update (PUT /api/tickets/<id>/)
# ==========================================

@pytest.mark.django_db
def test_update_ticket_superuser(api_client, superuser, get_auth_header, sample_ticket):
    """Verify Superuser can update ticket with partial fields (omitting event_id)."""
    headers = get_auth_header(superuser)
    update_data = {
        'name': 'VIP Updated Ticket',
        'price': 200000,
    }
    response = api_client.put(f'/api/tickets/{sample_ticket.id}/', update_data, format='json', **headers)
    assert response.status_code == status.HTTP_200_OK
    sample_ticket.refresh_from_db()
    assert sample_ticket.name == 'VIP Updated Ticket'
    assert sample_ticket.price == 200000

@pytest.mark.django_db
def test_update_ticket_organizer(api_client, organizer_user, get_auth_header, sample_ticket):
    """Verify Organizer can update ticket belonging to their event."""
    headers = get_auth_header(organizer_user)
    response = api_client.put(f'/api/tickets/{sample_ticket.id}/', {'quota': 150}, format='json', **headers)
    assert response.status_code == status.HTTP_200_OK
    sample_ticket.refresh_from_db()
    assert sample_ticket.quota == 150

@pytest.mark.django_db
def test_update_ticket_organizer_other_event_forbidden(api_client, organizer_group, get_auth_header, sample_ticket):
    """Verify Organizer cannot update ticket belonging to another Organizer's event (403 Forbidden)."""
    other_organizer = User.objects.create_user(
        username='other_organizer',
        email='other_organizer@dicoevent.com',
        password='password123'
    )
    other_organizer.groups.add(organizer_group)
    headers = get_auth_header(other_organizer)
    response = api_client.put(f'/api/tickets/{sample_ticket.id}/', {'quota': 999}, format='json', **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_update_ticket_regular_user_forbidden(api_client, regular_user, get_auth_header, sample_ticket):
    """Verify regular User cannot update ticket (403 Forbidden)."""
    headers = get_auth_header(regular_user)
    response = api_client.put(f'/api/tickets/{sample_ticket.id}/', {'name': 'Hacked'}, format='json', **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

# ==========================================
# 5. Ticket Deletion (DELETE /api/tickets/<id>/)
# ==========================================

@pytest.mark.django_db
def test_delete_ticket_superuser_and_subsequent_404(api_client, superuser, get_auth_header, sample_ticket):
    """Verify deleting ticket returns 204 and subsequent GET returns 404."""
    ticket_id = sample_ticket.id
    headers = get_auth_header(superuser)
    response = api_client.delete(f'/api/tickets/{ticket_id}/', **headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify subsequent GET returns 404 (with and without trailing slash)
    get_res1 = api_client.get(f'/api/tickets/{ticket_id}/')
    assert get_res1.status_code == status.HTTP_404_NOT_FOUND
    get_res2 = api_client.get(f'/api/tickets/{ticket_id}')
    assert get_res2.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_delete_ticket_organizer_own_ticket(api_client, organizer_user, get_auth_header, sample_ticket):
    """Verify Organizer can delete ticket belonging to their own event."""
    ticket_id = sample_ticket.id
    headers = get_auth_header(organizer_user)
    response = api_client.delete(f'/api/tickets/{ticket_id}/', **headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Ticket.objects.filter(id=ticket_id).exists()

@pytest.mark.django_db
def test_delete_ticket_organizer_other_event_forbidden(api_client, organizer_group, get_auth_header, sample_ticket):
    """Verify Organizer cannot delete ticket belonging to another Organizer's event (403 Forbidden)."""
    other_organizer = User.objects.create_user(
        username='other_organizer_del',
        email='other_organizer_del@dicoevent.com',
        password='password123'
    )
    other_organizer.groups.add(organizer_group)
    headers = get_auth_header(other_organizer)
    response = api_client.delete(f'/api/tickets/{sample_ticket.id}/', **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_delete_ticket_regular_user_forbidden(api_client, regular_user, get_auth_header, sample_ticket):
    """Verify regular user cannot delete ticket (403 Forbidden)."""
    headers = get_auth_header(regular_user)
    response = api_client.delete(f'/api/tickets/{sample_ticket.id}/', **headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
