import pytest
from unittest.mock import patch
from django.utils import timezone
from core.models import User
from events.models import Event
from tickets.models import Ticket
from registrations.models import Registration
from registrations.tasks import check_and_send_reminders

@pytest.fixture
def test_data(db):
    user = User.objects.create_user(username='reguser', password='pwd', email='user@test.com')
    event = Event.objects.create(
        name="Reminder Event",
        description="Event for reminder testing",
        location="Bandung",
        start_time=timezone.now() + timezone.timedelta(hours=2, minutes=5), # Di dalam jendela 2 jam + 15 menit
        end_time=timezone.now() + timezone.timedelta(hours=4),
        status="upcoming",
        quota=50,
        category="Seminar",
        organizer=user
    )
    ticket = Ticket.objects.create(
        event=event, 
        name="VIP", 
        price=100000, 
        quota=50,
        sales_start=timezone.now(),
        sales_end=timezone.now() + timezone.timedelta(days=1)
    )
    reg = Registration.objects.create(user=user, ticket=ticket, is_reminder_sent=False)
    return reg

@pytest.mark.django_db
class TestReminderTask:
    @patch('registrations.tasks.send_ticket_email.delay')
    def test_check_and_send_reminders(self, mock_send_email, test_data):
        """Unit test: Memastikan task celery check_and_send_reminders menemukan registrasi yang tepat dan memanggil email delay."""
        assert test_data.is_reminder_sent == False

        # Execute task
        result = check_and_send_reminders()

        # Cek apakah send_ticket_email dipanggil dengan argument yang benar
        mock_send_email.assert_called_once_with('user@test.com', 'reguser', test_data.id)

        # Cek database ter-update
        test_data.refresh_from_db()
        assert test_data.is_reminder_sent == True
        assert result == "Processed 1 reminders."
