import pytest
from django.urls import reverse
from django.utils import timezone
from core.models import User
from events.models import Event
from unittest.mock import patch

@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', password='testpassword', email='user@test.com')

@pytest.fixture
def event(db, user):
    return Event.objects.create(
        name="Tech Conference",
        description="A conference for tech enthusiasts",
        location="Jakarta",
        start_time=timezone.now() + timezone.timedelta(days=1),
        end_time=timezone.now() + timezone.timedelta(days=2),
        status="upcoming",
        quota=100,
        category="Technology",
        organizer=user
    )

@pytest.mark.django_db
class TestEventModel:
    def test_event_str(self, event):
        """Unit test: Memastikan representasi string dari model Event sesuai dengan nama event."""
        assert str(event) == "Tech Conference"

@pytest.mark.django_db
class TestEventAPIIntegration:
    @patch('events.views.cache.get', return_value=None)
    @patch('events.views.cache.set')
    def test_get_event_list_authenticated(self, mock_cache_set, mock_cache_get, user, event):
        """Integration test: Memastikan API list event mengembalikan data saat user terautentikasi."""
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=user)

        url = reverse('event-list')
        response = api_client.get(url)

        assert response.status_code == 200
        assert 'events' in response.data
        assert len(response.data['events']) == 1
        assert response.data['events'][0]['name'] == "Tech Conference"

    @patch('events.views.cache.get', return_value=None)
    def test_get_event_list_unauthenticated(self, mock_cache_get):
        """Integration test: Memastikan API list event menolak akses tanpa token (401)."""
        from rest_framework.test import APIClient
        api_client = APIClient()
        
        url = reverse('event-list')
        response = api_client.get(url)
        assert response.status_code == 401
